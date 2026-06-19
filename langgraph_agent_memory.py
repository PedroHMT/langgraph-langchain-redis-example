"""
LangGraph Agent - ReAct Pattern
"""
from dotenv import load_dotenv
load_dotenv()

import operator
from typing import TypedDict, Annotated

# LangGraph -> Orquestrar o fluxo de execução em grafos
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# LangChain -> Operar a LLM
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# Memory
from langgraph.checkpoint.memory import MemorySaver

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
    
    response = llm.invoke(state["messages"])
    
    if response.tool_calls:
        print(f"    LLM quer chamar {len(response.tool_calls)} tool(s):")
        for tc in response.tool_calls:
            print(f"       → {tc['name']}({tc['args']})")
    else:
        print(f"    LLM respondeu diretamente:")
        print(f"       {response.content[:100]}...")
    
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

# Create Graph with State Type
graph = StateGraph(State)

# Add Nodes
graph.add_node("agent", agent_node)           # Node that call the LLM
graph.add_node("tools", ToolNode(tools))      # Node that execute tools (ToolNode() -> Schema for tool calling)

# Define Entry Point
graph.set_entry_point("agent")

# Define Conditional Edge 
graph.add_conditional_edges("agent", should_continue)

# Define Edge (Tools -> Agent everytime)
graph.add_edge("tools", "agent")

# Define Checkpoint for MemorySaver
memory = MemorySaver()

# Compile Graph with Checkpoint
app = graph.compile(checkpointer=memory)

print("✅ Grafo compilado!")

def run_agent(pergunta: str, thread_id: str):
    """Executa o agente com uma pergunta."""
    print("\n" + "=" * 50)
    print(f"📝 PERGUNTA: {pergunta}")
    print(f"[THREAD ID]: {thread_id}")
    print("=" * 50)
    
    # Initial State -> only the user message
    initial_state = {
        "messages": [("user", pergunta)]
    }

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Execute the graph
    result = app.invoke(initial_state, config=config)
    
    # Get the last message (final response)
    final_message = result["messages"][-1]
    
    print("\n" + "=" * 50)
    print("✅ RESPOSTA FINAL:")
    print("=" * 50)
    print(final_message.content)
    
    return final_message.content

if __name__ == "__main__":
    print("\n" + "🧠" * 20)
    print("LANGGRAPH AGENT - TESTE DE MEMÓRIA")
    print("🧠" * 20)
    
    print("\n\n" + "━" * 60)
    print("TESTE 1: Multi-turno (mesmo usuário)")
    print("O agente deve LEMBRAR das mensagens anteriores")
    print("━" * 60)
    
    THREAD_USER_42 = "user-42-sessao-1"
    
    # Turn 1
    run_agent("Oi! Meu nome é Pedro.", THREAD_USER_42)
    
    input("\n[ENTER para continuar...]")
    
    # Turn 2 - Agent should remember the name
    run_agent("Qual é o meu nome?", THREAD_USER_42)
    
    input("\n[ENTER para continuar...]")
    
    # Turno 3 - Mais contexto
    run_agent("Busque as informações do usuário 42.", THREAD_USER_42)
    
    input("\n[ENTER para continuar...]")
    
    # Turno 4 - Deve lembrar de tudo
    run_agent("Resuma tudo que conversamos até agora.", THREAD_USER_42)
    
    # ==========================================
    # TESTE 2: Thread diferente (outro usuário)
    # ==========================================
    print("\n\n" + "━" * 60)
    print("TESTE 2: Thread diferente (outro usuário)")
    print("O agente NÃO deve saber quem é Pedro")
    print("━" * 60)
    
    input("\n[ENTER para continuar...]")
    
    THREAD_USER_99 = "user-99-sessao-1"
    
    # Este é um usuário DIFERENTE - não sabe nada do user-42
    run_agent("Qual é o meu nome?", THREAD_USER_99)
    
    # ==========================================
    # TESTE 3: Voltar ao user-42
    # ==========================================
    print("\n\n" + "━" * 60)
    print("TESTE 3: Voltar ao user-42")
    print("O agente deve AINDA lembrar de Pedro")
    print("━" * 60)
    
    input("\n[ENTER para continuar...]")
    
    run_agent("Você ainda lembra meu nome?", THREAD_USER_42)
    
    print("\n\n" + "✅" * 20)
    print("TESTES CONCLUÍDOS!")
    print("✅" * 20)