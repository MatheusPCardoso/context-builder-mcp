"""
Utilitários de arquivo para contexto com IA.

Ferramentas para preparar arquivos e pastas de forma otimizada
para enviar como contexto para IAs, economizando tokens.
"""

from pathlib import Path
from typing import Any
from ..context import mcp

# Extensões de código suportadas
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".toml",
    ".md", ".sh", ".sql",
}

# Pastas e arquivos para ignorar
IGNORE_PATTERNS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache",
}

# Arquivos sensíveis que nunca devem ser lidos
SENSITIVE_FILES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "id_rsa.pub", "id_ed25519.pub",
    ".netrc", ".pgpass", "credentials", "secrets.json",
    "service-account.json", "keystore.jks", ".htpasswd",
}

# Limite de tamanho máximo para leitura (1MB)
MAX_FILE_SIZE = 1_000_000
# Limite total de caracteres retornados
MAX_TOTAL_CHARS = 500_000


def _should_ignore(name: str) -> bool:
    """Verifica se um arquivo/pasta deve ser ignorado."""
    return name in IGNORE_PATTERNS or name.startswith(".")


def _is_sensitive_file(path: Path) -> bool:
    """Verifica se um arquivo é potencialmente sensível."""
    name = path.name.lower()
    # Bloqueia arquivos sensíveis conhecidos
    if name in SENSITIVE_FILES:
        return True
    # Bloqueia qualquer .env* (ex: .env.local, .env.test)
    if name.startswith(".env"):
        return True
    # Bloqueia arquivos de chave privada
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".cer", ".crt")):
        return True
    return False


def _resolve_safe_path(raw_path: str, base_path: Path | None = None) -> Path | None:
    """
    Resolve o path e garante que não há path traversal.

    Se base_path for fornecido, o arquivo deve estar dentro dele.
    Retorna None se o path for considerado inseguro.
    """
    try:
        resolved = Path(raw_path).resolve()
    except Exception:
        return None

    if base_path is not None:
        try:
            resolved.relative_to(base_path.resolve())
        except ValueError:
            # Path está fora do diretório base — path traversal bloqueado
            return None

    return resolved


def _get_tree(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> list[str]:
    """Gera árvore de diretório recursivamente."""
    if current_depth >= max_depth:
        return []

    lines = []
    try:
        entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
    except PermissionError:
        return []

    entries = [e for e in entries if not _should_ignore(e.name)]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(_get_tree(entry, prefix + extension, max_depth, current_depth + 1))

    return lines


@mcp.tool("summarize_project")
def summarize_project(path: str, max_depth: int = 3) -> dict[str, Any]:
    """Gera um resumo estrutural do projeto para usar como contexto com IA.

    Mostra a árvore de arquivos ignorando pastas desnecessárias (node_modules, etc.)
    e lista os arquivos de configuração principais encontrados.
    Arquivos sensíveis (.env, chaves, certificados) são omitidos da listagem.

    Args:
        path: Caminho para a pasta do projeto
        max_depth: Profundidade máxima da árvore (padrão: 3, máximo: 6)

    Returns:
        Estrutura do projeto formatada para contexto de IA
    """
    root = Path(path).resolve()
    if not root.exists():
        return {"status": "error", "message": f"Caminho não encontrado: {path}"}

    if not root.is_dir():
        return {"status": "error", "message": f"'{path}' não é uma pasta"}

    # Limita profundidade para evitar travessia excessiva
    max_depth = min(max_depth, 6)

    # Gera árvore
    tree_lines = [root.name + "/"] + _get_tree(root, max_depth=max_depth)
    tree = "\n".join(tree_lines)

    # Detecta arquivos de configuração relevantes (sem sensíveis)
    config_files = []
    config_names = {
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "tsconfig.json", "vite.config.ts", "webpack.config.js",
        "docker-compose.yml", "Dockerfile", "README.md",
        # .env.example é seguro (não contém valores reais)
        ".env.example",
    }
    for name in config_names:
        candidate = root / name
        if candidate.exists() and not _is_sensitive_file(candidate):
            config_files.append(name)

    # Conta arquivos por extensão
    ext_count: dict[str, int] = {}
    for f in root.rglob("*"):
        if f.is_file() and not any(_should_ignore(part) for part in f.parts):
            if _is_sensitive_file(f):
                continue
            ext = f.suffix.lower()
            if ext in CODE_EXTENSIONS:
                ext_count[ext] = ext_count.get(ext, 0) + 1

    return {
        "tree": tree,
        "config_files_found": config_files,
        "file_counts_by_extension": dict(sorted(ext_count.items(), key=lambda x: -x[1])),
        "tip": "Use este resumo como contexto inicial ao pedir ajuda sobre o projeto",
    }


@mcp.tool("read_files_for_ai")
def read_files_for_ai(paths: list[str], include_line_numbers: bool = False) -> dict[str, Any]:
    """Lê múltiplos arquivos e formata o conteúdo otimizado para enviar para IA.

    Concatena os arquivos com separadores claros e informações de contexto.
    Arquivos sensíveis (.env, chaves privadas, certificados) são bloqueados.

    Args:
        paths: Lista de caminhos de arquivos para ler (máximo 20 arquivos)
        include_line_numbers: Se True, adiciona números de linha (útil para debug)

    Returns:
        Conteúdo formatado de todos os arquivos com metadados
    """
    # Limita quantidade de arquivos por chamada
    if len(paths) > 20:
        return {"status": "error", "message": "Máximo de 20 arquivos por chamada."}

    results = []
    total_chars = 0
    errors = []

    for file_path in paths:
        resolved = _resolve_safe_path(file_path)
        if resolved is None:
            errors.append(f"Path inválido ou inseguro: {file_path}")
            continue

        if not resolved.exists():
            errors.append(f"Não encontrado: {file_path}")
            continue

        if not resolved.is_file():
            errors.append(f"Não é um arquivo: {file_path}")
            continue

        # Bloqueia arquivos sensíveis
        if _is_sensitive_file(resolved):
            errors.append(f"Bloqueado por segurança (arquivo sensível): {resolved.name}")
            continue

        # Verifica tamanho antes de ler
        try:
            size = resolved.stat().st_size
        except OSError as e:
            errors.append(f"Erro ao acessar {file_path}: {e}")
            continue

        if size > MAX_FILE_SIZE:
            errors.append(f"Arquivo muito grande ({size // 1024}KB, máximo 1MB): {file_path}")
            continue

        # Verifica limite total acumulado
        if total_chars >= MAX_TOTAL_CHARS:
            errors.append(f"Limite total de caracteres atingido, ignorando: {file_path}")
            continue

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            ext = resolved.suffix.lstrip(".")

            if include_line_numbers:
                lines = content.splitlines()
                content = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))

            formatted = f"### {file_path}\n```{ext}\n{content}\n```"
            results.append(formatted)
            total_chars += len(content)

        except OSError as e:
            errors.append(f"Erro ao ler {file_path}: {e}")

    combined = "\n\n".join(results)

    return {
        "content": combined,
        "files_read": len(results),
        "total_chars": total_chars,
        "errors": errors,
        "tip": "Cole o campo 'content' diretamente no chat com a IA",
    }


@mcp.tool("find_relevant_files")
def find_relevant_files(path: str, keywords: list[str], extensions: list[str] | None = None) -> dict[str, Any]:
    """Encontra arquivos relevantes em um projeto baseado em palavras-chave.

    Busca nos nomes de arquivo e no conteúdo para identificar quais arquivos
    são mais relevantes para uma tarefa específica.
    Arquivos sensíveis são excluídos dos resultados.

    Args:
        path: Pasta raiz para buscar
        keywords: Palavras-chave para buscar (ex: ["auth", "login", "token"])
        extensions: Extensões para filtrar (ex: [".py", ".ts"]). None = todas.

    Returns:
        Lista de arquivos relevantes com score de relevância
    """
    # Limita quantidade de keywords para evitar buscas abusivas
    if len(keywords) > 20:
        return {"status": "error", "message": "Máximo de 20 keywords por busca."}

    root = _resolve_safe_path(path)
    if root is None or not root.exists():
        return {"status": "error", "message": f"Caminho não encontrado ou inválido: {path}"}

    if not root.is_dir():
        return {"status": "error", "message": f"'{path}' não é uma pasta"}

    filter_exts = set(extensions) if extensions else CODE_EXTENSIONS
    matches: list[dict[str, Any]] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if any(_should_ignore(part) for part in file_path.parts):
            continue
        if file_path.suffix.lower() not in filter_exts:
            continue

        # Nunca expõe arquivos sensíveis nos resultados
        if _is_sensitive_file(file_path):
            continue

        score = 0
        matched_keywords = []

        # Verifica nome do arquivo
        name_lower = file_path.name.lower()
        for kw in keywords:
            if kw.lower() in name_lower:
                score += 3
                matched_keywords.append(f"nome: {kw}")

        # Verifica conteúdo (apenas arquivos dentro do limite de tamanho)
        try:
            file_size = file_path.stat().st_size
            if file_size < MAX_FILE_SIZE:
                content = file_path.read_text(encoding="utf-8", errors="replace").lower()
                for kw in keywords:
                    count = content.count(kw.lower())
                    if count > 0:
                        score += min(count, 5)
                        matched_keywords.append(f"conteúdo: {kw} ({count}x)")
        except OSError:
            # Falha explícita registrada no match se o arquivo já tinha score por nome
            if score > 0:
                matched_keywords.append("(erro ao ler conteúdo)")

        if score > 0:
            matches.append({
                "path": str(file_path),
                "score": score,
                "matched": matched_keywords,
            })

    matches.sort(key=lambda x: -x["score"])

    return {
        "files_found": len(matches),
        "results": matches[:20],  # top 20
        "tip": "Use read_files_for_ai com os paths mais relevantes para montar o contexto",
    }
