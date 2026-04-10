"""
Memória temporária de sessão.

Permite salvar e recuperar snippets, notas e contexto durante uma sessão de trabalho.
Útil para passar informações entre conversas ou manter contexto sem repetir.
"""

from typing import Any
from ..context import mcp

# Armazenamento em memória (dura enquanto o servidor estiver rodando)
_store: dict[str, Any] = {}

# Limites para evitar abuso de memória
MAX_ENTRIES = 100
MAX_KEY_LEN = 128
MAX_VALUE_LEN = 50_000  # 50KB por entrada


@mcp.tool("memory_save")
def memory_save(key: str, value: str) -> dict[str, str]:
    """Salva um valor na memória temporária da sessão.

    Use para guardar: snippets de código, contexto de projeto,
    decisões tomadas, ou qualquer texto que você queira reutilizar.

    Args:
        key: Nome/identificador para recuperar depois (ex: "stack_do_projeto")
        value: Conteúdo a salvar

    Returns:
        Confirmação do que foi salvo
    """
    if len(key) > MAX_KEY_LEN:
        return {"status": "error", "message": f"Chave muito longa (máximo {MAX_KEY_LEN} caracteres)."}

    if len(value) > MAX_VALUE_LEN:
        return {"status": "error", "message": f"Valor muito grande (máximo {MAX_VALUE_LEN // 1000}KB)."}

    if key not in _store and len(_store) >= MAX_ENTRIES:
        return {"status": "error", "message": f"Limite de {MAX_ENTRIES} entradas atingido. Delete alguma antes de salvar."}

    _store[key] = value
    return {"status": "saved", "key": key, "preview": value[:100] + "..." if len(value) > 100 else value}


@mcp.tool("memory_get")
def memory_get(key: str = "") -> dict[str, Any]:
    """Recupera valor(es) da memória temporária.

    Args:
        key: Chave específica para buscar. Se vazio, retorna todas as chaves salvas.

    Returns:
        Valor salvo ou lista de chaves disponíveis
    """
    if not key:
        return {"keys": list(_store.keys()), "count": len(_store)}

    if key not in _store:
        return {"status": "not_found", "key": key, "available_keys": list(_store.keys())}

    return {"key": key, "value": _store[key]}


@mcp.tool("memory_delete")
def memory_delete(key: str) -> dict[str, str]:
    """Remove uma entrada da memória.

    Args:
        key: Chave a remover

    Returns:
        Confirmação da remoção
    """
    if key in _store:
        del _store[key]
        return {"status": "deleted", "key": key}
    return {"status": "not_found", "key": key}
