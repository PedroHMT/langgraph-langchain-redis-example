"""
LangGraph Agent - ReAct Pattern
Estudo passo a passo
"""
from dotenv import load_dotenv
load_dotenv()

import operator
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def buscar_usuario(user_id: int) -> dict:
    """
    Busca informações de um usuário pelo ID.
    Retorna nome, email e plano do usuário.
    
    Args:
        user_id: O ID único do usuário (número inteiro)
    """
    usuarios = {
        42: {"nome": "Pedro Silva", "email": "pedro@email.com", "plano": "premium"},
        123: {"nome": "Maria Santos", "email": "maria@email.com", "plano": "free"},
        456: {"nome": "João Costa", "email": "joao@email.com", "plano": "enterprise"},
    }
    
    print(f"    🔧 [TOOL] buscar_usuario({user_id})")
    
    if user_id in usuarios:
        return {"sucesso": True, "usuario": usuarios[user_id]}
    return {"sucesso": False, "erro": f"Usuário {user_id} não encontrado"}


@tool
def listar_sessoes(user_id: int) -> dict:
    """
    Lista todas as sessões de um usuário.
    Retorna histórico com data e duração de cada sessão.
    
    Args:
        user_id: O ID do usuário para listar as sessões
    """
    sessoes = {
        42: [
            {"id": "sess_1", "data": "2024-01-15", "duracao_min": 45},
            {"id": "sess_2", "data": "2024-01-16", "duracao_min": 30},
        ],
        123: [{"id": "sess_3", "data": "2024-01-10", "duracao_min": 20}],
        456: [],
    }
    
    print(f"    🔧 [TOOL] listar_sessoes({user_id})")
    
    if user_id in sessoes:
        return {"sucesso": True, "total": len(sessoes[user_id]), "sessoes": sessoes[user_id]}
    return {"sucesso": False, "erro": f"Usuário {user_id} não encontrado"}


tools = [buscar_usuario, listar_sessoes]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, operator.add]

def agent_node(state: State) -> dict:
    """
    Nó do agente: chama o LLM com as mensagens atuais.
    Recebe o estado, retorna apenas o DELTA (novas mensagens).
    """
    print("\n" + "─" * 40)
    print("🤖 [AGENT] Chamando LLM...")
    
    # Chama o LLM com todas as mensagens do estado
    response = llm.invoke(state["messages"])
    
    # Debug: mostra o que o LLM decidiu
    if response.tool_calls:
        print(f"    LLM quer chamar {len(response.tool_calls)} tool(s):")
        for tc in response.tool_calls:
            print(f"       → {tc['name']}({tc['args']})")
    else:
        print(f"    LLM respondeu diretamente:")
        print(f"       {response.content[:100]}...")
    
    # Retorna DELTA (só a nova mensagem)
    return {"messages": [response]}


def should_continue(state: State) -> str:
    """
    Função de roteamento: decide o próximo nó.
    Olha a última mensagem e decide:
      - Se tem tool_calls → vai para 'tools'
      - Se não tem → vai para END
    """
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        print("    ➡️  Roteando para: TOOLS")
        return "tools"
    else:
        print("    ➡️  Roteando para: END")
        return END

print("🔨 Construindo o grafo...")

# 1. Criar o grafo com o tipo de State
graph = StateGraph(State)

# 2. Adicionar os nós
graph.add_node("agent", agent_node)           # Nó que chama o LLM
graph.add_node("tools", ToolNode(tools))      # Nó que executa tools (pré-construído)

# 3. Definir ponto de entrada (por onde começa)
graph.set_entry_point("agent")

# 4. Adicionar edges (caminhos)
#    - Edge condicional: agent → tools OU END (depende do estado)
graph.add_conditional_edges("agent", should_continue)

#    - Edge fixo: tools → agent (sempre volta)
graph.add_edge("tools", "agent")

# 5. Compilar o grafo (transforma em algo executável)
app = graph.compile()

print("✅ Grafo compilado!")

def run_agent(pergunta: str):
    """Executa o agente com uma pergunta."""
    print("\n" + "=" * 50)
    print(f"📝 PERGUNTA: {pergunta}")
    print("=" * 50)
    
    # Estado inicial: só a mensagem do usuário
    initial_state = {
        "messages": [("user", pergunta)]
    }
    
    # Executar o grafo
    result = app.invoke(initial_state)
    
    # Pegar a última mensagem (resposta final)
    final_message = result["messages"][-1]
    
    print("\n" + "=" * 50)
    print("✅ RESPOSTA FINAL:")
    print("=" * 50)
    print(final_message.content)
    
    return final_message.content

if __name__ == "__main__":
    print("\n" + "🚀" * 20)
    print("LANGGRAPH AGENT - ReAct Pattern")
    print("🚀" * 20)
    
    # Teste 1: Busca simples (uma tool)
    print("\n\n" + "─" * 50)
    print("TESTE 1: Busca simples")
    print("─" * 50)
    run_agent("Qual o nome e email do usuário 42?")
    
    input("\n\nPressione ENTER para o próximo teste...")
    
    # Teste 2: Múltiplas tools (parallel tool calling)
    print("\n\n" + "─" * 50)
    print("TESTE 2: Múltiplas tools")
    print("─" * 50)
    run_agent("Me diga o plano do usuário 42 e liste suas sessões")
    
    input("\n\nPressione ENTER para o próximo teste...")
    
    # Teste 3: Usuário não existe
    print("\n\n" + "─" * 50)
    print("TESTE 3: Usuário inexistente")
    print("─" * 50)
    run_agent("Qual o email do usuário 999?")
    
    input("\n\nPressione ENTER para o próximo teste...")
    
    # Teste 4: Pergunta que NÃO precisa de tools
    print("\n\n" + "─" * 50)
    print("TESTE 4: Sem tools")
    print("─" * 50)
    run_agent("Quanto é 15 + 27?")