# context-builder

MCP pessoal para otimizar o uso com IA no desenvolvimento. Construir e gerenciar contexto para interações com IA de forma leve e focada.

## Ferramentas

| Tool | O que faz |
|------|-----------|
| `memory_save` | Salva contexto ou snippets na sessão atual |
| `memory_get` | Recupera o que foi salvo |
| `memory_delete` | Remove uma entrada da memória |
| `build_prompt` | Gera prompts estruturados para tarefas comuns |
| `list_prompt_templates` | Lista os templates de prompt disponíveis |
| `summarize_project` | Resume a estrutura de um projeto para usar como contexto |
| `read_files_for_ai` | Lê e formata múltiplos arquivos para enviar para IA |
| `find_relevant_files` | Encontra arquivos relevantes por palavras-chave |

## Templates de prompt disponíveis

- `code_review` — revisão com severidade dos problemas
- `explain_code` — explicação detalhada do funcionamento
- `refactor` — refatoração com objetivos específicos
- `write_tests` — geração de testes com edge cases
- `debug` — diagnóstico e solução de erros
- `architecture` — design de arquitetura para novas features

## Segurança

- Sem conexões externas — 100% local via stdio
- Bloqueia leitura de arquivos sensíveis (`.env*`, chaves privadas, certificados)
- Proteção contra path traversal
- Limites de tamanho e quantidade por chamada

## Instalação

```bash
pip install -e .
# ou
uv pip install -e .
```

## Configuração

Adicione em `~/.kiro/settings/mcp.json` (Kiro) ou no config do Claude Desktop:

```json
{
  "mcpServers": {
    "context-builder": {
      "command": "python",
      "args": ["-m", "context_builder"],
      "cwd": "/caminho/para/context-builder"
    }
  }
}
```

## Inspiração

Baseado na arquitetura do [lucidity-mcp](https://github.com/hyperbliss/lucidity) de [@hyperbliss](https://github.com/hyperbliss).
O lucidity usa o mesmo padrão FastMCP + stdio para entregar análise de código via git diff.
O context-builder expande essa ideia para cobrir o fluxo completo de trabalho com IA: memória de sessão, geração de prompts e preparação de contexto de projeto.
