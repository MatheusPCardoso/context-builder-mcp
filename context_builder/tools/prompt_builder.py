"""
Gerador de prompts otimizados.

Cria prompts estruturados para tarefas comuns com IA,
economizando tempo e melhorando a qualidade das respostas.
"""

from typing import Any
from ..context import mcp

# Templates de prompts para tarefas comuns
PROMPT_TEMPLATES = {
    "code_review": """Faça uma revisão de código focando em:
1. Bugs e problemas de lógica
2. Performance e eficiência
3. Segurança
4. Legibilidade e manutenibilidade
5. Boas práticas da linguagem {language}

Código:
```{language}
{code}
```

Para cada problema encontrado, informe: localização, severidade (alta/média/baixa) e sugestão de correção.""",

    "explain_code": """Explique o seguinte código {language} de forma clara e objetiva:

```{language}
{code}
```

Inclua:
- O que o código faz (visão geral)
- Como funciona passo a passo
- Pontos de atenção ou complexidades
- Para que casos de uso seria útil""",

    "refactor": """Refatore o seguinte código {language} mantendo o comportamento original:

```{language}
{code}
```

Objetivos do refactor:
{goals}

Mostre o código refatorado e explique cada mudança feita.""",

    "write_tests": """Escreva testes para o seguinte código {language}:

```{language}
{code}
```

Framework de testes: {framework}
Cobertura esperada:
- Casos felizes (happy path)
- Casos de erro e edge cases
- Mocks necessários

Inclua comentários explicando o que cada teste verifica.""",

    "debug": """Estou com o seguinte erro:

```
{error}
```

Contexto do código:
```{language}
{code}
```

Analise a causa raiz do erro e forneça:
1. Explicação do que está causando o problema
2. Solução passo a passo
3. Como evitar esse tipo de erro no futuro""",

    "architecture": """Preciso de ajuda para arquitetar: {feature}

Contexto do projeto:
{context}

Forneça:
1. Abordagem recomendada com justificativa
2. Estrutura de arquivos/módulos sugerida
3. Interfaces e contratos principais
4. Trade-offs da abordagem
5. Alternativas consideradas""",
}


@mcp.tool("build_prompt")
def build_prompt(
    template: str,
    code: str = "",
    language: str = "python",
    error: str = "",
    feature: str = "",
    context: str = "",
    goals: str = "melhorar legibilidade, reduzir complexidade",
    framework: str = "pytest",
) -> dict[str, Any]:
    """Gera um prompt otimizado para uma tarefa específica com IA.

    Args:
        template: Tipo de tarefa. Opções: code_review, explain_code, refactor,
                  write_tests, debug, architecture
        code: Código relevante para a tarefa
        language: Linguagem de programação (python, typescript, etc.)
        error: Mensagem de erro (para template 'debug')
        feature: Descrição da feature (para template 'architecture')
        context: Contexto adicional do projeto
        goals: Objetivos do refactor (para template 'refactor')
        framework: Framework de testes (para template 'write_tests')

    Returns:
        Prompt formatado pronto para usar com qualquer IA
    """
    if template not in PROMPT_TEMPLATES:
        return {
            "status": "error",
            "message": f"Template '{template}' não encontrado.",
            "available_templates": list(PROMPT_TEMPLATES.keys()),
        }

    prompt = PROMPT_TEMPLATES[template]
    # Substituição manual para evitar que inputs do usuário acessem
    # atributos internos via {__class__}, {__dict__}, etc.
    replacements = {
        "{language}": language,
        "{code}": code,
        "{error}": error,
        "{feature}": feature,
        "{context}": context,
        "{goals}": goals,
        "{framework}": framework,
    }
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)

    return {
        "template": template,
        "prompt": prompt,
        "char_count": len(prompt),
        "tip": "Cole este prompt diretamente no chat com a IA",
    }


@mcp.tool("list_prompt_templates")
def list_prompt_templates() -> dict[str, Any]:
    """Lista todos os templates de prompt disponíveis com descrição.

    Returns:
        Dicionário com templates disponíveis e seus casos de uso
    """
    descriptions = {
        "code_review": "Revisão completa de código com severidade dos problemas",
        "explain_code": "Explicação detalhada de como um código funciona",
        "refactor": "Refatoração com objetivos específicos mantendo comportamento",
        "write_tests": "Geração de testes com cobertura de edge cases",
        "debug": "Diagnóstico e solução de erros",
        "architecture": "Design de arquitetura para novas features",
    }
    return {"templates": descriptions, "count": len(descriptions)}
