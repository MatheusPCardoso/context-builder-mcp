"""
Ferramentas de contexto para desenvolvimento.

Coleta informações do ambiente de desenvolvimento de forma leve
para usar como contexto com IA sem consumir tokens desnecessários.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from ..context import mcp


def _run(cmd: list[str], cwd: str) -> str:
    """Executa um comando e retorna stdout, ou string vazia em caso de erro."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


@mcp.tool("git_diff_context")
def git_diff_context(path: str, staged_only: bool = False) -> dict[str, Any]:
    """Retorna o git diff atual formatado para enviar como contexto para IA.

    Mantém o output enxuto: só arquivos modificados e o diff resumido.
    Ideal para pedir revisão ou ajuda sem copiar e colar manualmente.

    Args:
        path: Caminho do repositório git
        staged_only: Se True, retorna apenas mudanças staged (prontas para commit)

    Returns:
        Diff formatado com lista de arquivos e mudanças
    """
    root = Path(path).resolve()
    if not root.exists():
        return {"status": "error", "message": f"Caminho não encontrado: {path}"}

    if not (root / ".git").exists():
        return {"status": "error", "message": "Nenhum repositório git encontrado neste caminho."}

    cwd = str(root)

    # Branch e último commit (contexto mínimo)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    last_commit = _run(["git", "log", "-1", "--pretty=%h %s"], cwd)

    # Arquivos modificados
    if staged_only:
        files_out = _run(["git", "diff", "--cached", "--name-status"], cwd)
        diff_out = _run(["git", "diff", "--cached", "--stat"], cwd)
        raw_diff = _run(["git", "diff", "--cached"], cwd)
    else:
        files_out = _run(["git", "diff", "HEAD", "--name-status"], cwd)
        diff_out = _run(["git", "diff", "HEAD", "--stat"], cwd)
        raw_diff = _run(["git", "diff", "HEAD"], cwd)

    if not raw_diff:
        return {
            "status": "no_changes",
            "branch": branch,
            "last_commit": last_commit,
            "message": "Nenhuma mudança detectada.",
        }

    # Limita o diff a 8000 chars para não explodir o contexto
    truncated = False
    if len(raw_diff) > 8000:
        raw_diff = raw_diff[:8000]
        truncated = True

    return {
        "branch": branch,
        "last_commit": last_commit,
        "changed_files": files_out,
        "stat": diff_out,
        "diff": raw_diff,
        "truncated": truncated,
        "tip": "Envie 'diff' + 'stat' para a IA — é o suficiente para revisão",
    }


@mcp.tool("list_dependencies")
def list_dependencies(path: str) -> dict[str, Any]:
    """Lê as dependências do projeto a partir dos arquivos de manifesto.

    Suporta: package.json (Node), pyproject.toml (Python), Cargo.toml (Rust),
    go.mod (Go). Retorna apenas nomes e versões, sem instalar nada.

    Args:
        path: Caminho raiz do projeto

    Returns:
        Dependências organizadas por tipo (produção/desenvolvimento)
    """
    root = Path(path).resolve()
    if not root.exists():
        return {"status": "error", "message": f"Caminho não encontrado: {path}"}

    result: dict[str, Any] = {"path": str(root), "found": []}

    # --- package.json (Node/Bun/Deno) ---
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            result["found"].append("package.json")
            result["node"] = {
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "dependencies": data.get("dependencies", {}),
                "devDependencies": data.get("devDependencies", {}),
            }
        except Exception:
            result["node_error"] = "Erro ao ler package.json"

    # --- pyproject.toml (Python) ---
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            # Leitura manual simples para não depender de tomllib em <3.11
            import tomllib  # disponível no Python 3.11+
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = data.get("project", {})
            result["found"].append("pyproject.toml")
            result["python"] = {
                "name": project.get("name", ""),
                "version": project.get("version", ""),
                "requires_python": project.get("requires-python", ""),
                "dependencies": project.get("dependencies", []),
                "dev_dependencies": (
                    data.get("dependency-groups", {}).get("dev", [])
                    or data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
                ),
            }
        except Exception:
            result["python_error"] = "Erro ao ler pyproject.toml"

    # --- Cargo.toml (Rust) ---
    cargo = root / "Cargo.toml"
    if cargo.exists():
        try:
            import tomllib
            data = tomllib.loads(cargo.read_text(encoding="utf-8"))
            result["found"].append("Cargo.toml")
            result["rust"] = {
                "name": data.get("package", {}).get("name", ""),
                "version": data.get("package", {}).get("version", ""),
                "dependencies": {k: str(v) for k, v in data.get("dependencies", {}).items()},
                "dev_dependencies": {k: str(v) for k, v in data.get("dev-dependencies", {}).items()},
            }
        except Exception:
            result["rust_error"] = "Erro ao ler Cargo.toml"

    # --- go.mod (Go) ---
    gomod = root / "go.mod"
    if gomod.exists():
        try:
            lines = gomod.read_text(encoding="utf-8").splitlines()
            module = next((l.split()[1] for l in lines if l.startswith("module ")), "")
            go_version = next((l.split()[1] for l in lines if l.startswith("go ")), "")
            requires = [
                l.strip().lstrip("require").strip()
                for l in lines
                if l.strip().startswith("require") or (l.startswith("\t") and "//" not in l)
            ]
            result["found"].append("go.mod")
            result["go"] = {
                "module": module,
                "go_version": go_version,
                "requires": [r for r in requires if r],
            }
        except Exception:
            result["go_error"] = "Erro ao ler go.mod"

    if not result["found"]:
        return {"status": "not_found", "message": "Nenhum arquivo de dependências encontrado.", "path": str(root)}

    return result


@mcp.tool("project_info")
def project_info(path: str) -> dict[str, Any]:
    """Detecta automaticamente informações do projeto e do ambiente de desenvolvimento.

    Coleta: linguagem principal, framework detectado, versão do runtime,
    estrutura básica e ferramentas de build. Leve — sem instalar nada.

    Args:
        path: Caminho raiz do projeto

    Returns:
        Resumo do projeto para usar como contexto inicial com IA
    """
    root = Path(path).resolve()
    if not root.exists():
        return {"status": "error", "message": f"Caminho não encontrado: {path}"}

    cwd = str(root)
    info: dict[str, Any] = {"path": cwd}

    # --- Detecta linguagem principal pelos arquivos presentes ---
    indicators = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "node": ["package.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "java": ["pom.xml", "build.gradle"],
        "dotnet": ["*.csproj", "*.sln"],
    }
    detected_langs = []
    for lang, files in indicators.items():
        for f in files:
            if "*" in f:
                if list(root.glob(f)):
                    detected_langs.append(lang)
                    break
            elif (root / f).exists():
                detected_langs.append(lang)
                break
    info["languages"] = detected_langs

    # --- Detecta framework pelo package.json ou pyproject ---
    frameworks = []
    pkg = root / "package.json"
    if pkg.exists():
        try:
            deps = json.loads(pkg.read_text(encoding="utf-8"))
            all_deps = {
                **deps.get("dependencies", {}),
                **deps.get("devDependencies", {}),
            }
            for fw in ["next", "react", "vue", "svelte", "astro", "express", "fastify", "nuxt"]:
                if fw in all_deps:
                    frameworks.append(fw)
        except Exception:
            pass

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8").lower()
            for fw in ["fastapi", "django", "flask", "litestar", "starlette", "tornado"]:
                if fw in content:
                    frameworks.append(fw)
        except Exception:
            pass
    info["frameworks"] = frameworks

    # --- Versão do runtime ---
    runtimes: dict[str, str] = {}
    for cmd, key in [
        (["python", "--version"], "python"),
        (["node", "--version"], "node"),
        (["go", "version"], "go"),
        (["rustc", "--version"], "rust"),
    ]:
        out = _run(cmd, cwd)
        if out:
            runtimes[key] = out.split("\n")[0]
    info["runtimes"] = runtimes

    # --- Git info básico ---
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if branch:
        info["git"] = {
            "branch": branch,
            "last_commit": _run(["git", "log", "-1", "--pretty=%h %s"], cwd),
        }

    # --- Ferramentas de build/test detectadas ---
    tools_detected = []
    tool_files = {
        "docker": "Dockerfile",
        "docker-compose": "docker-compose.yml",
        "makefile": "Makefile",
        "github-actions": ".github/workflows",
        "vite": "vite.config.ts",
        "webpack": "webpack.config.js",
        "jest": "jest.config.js",
        "pytest": "pytest.ini",
    }
    for tool, file in tool_files.items():
        if (root / file).exists():
            tools_detected.append(tool)
    info["tools"] = tools_detected

    return info
