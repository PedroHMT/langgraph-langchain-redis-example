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
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        print("    ➡️  Roteando para: TOOLS")
        return "tools"
    else:
        print("    ➡️  Roteando para: END")
        return END


graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")


def run_agent(app, pergunta: str, thread_id: str):
    print("\n" + "=" * 50)
    print(f"📝 PERGUNTA: {pergunta}")
    print(f"[THREAD ID]: {thread_id}")
    print("=" * 50)
    
    initial_state = {"messages": [("user", pergunta)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    result = app.invoke(initial_state, config=config)
    final_message = result["messages"][-1]
    
    print("\n" + "=" * 50)
    print("✅ RESPOSTA FINAL:")
    print("=" * 50)
    print(final_message.content)
    return final_message.content


if __name__ == "__main__":
    from langgraph.checkpoint.redis import RedisSaver
    
    REDIS_URL = "redis://localhost:6379"
    
    print("🔌 Conectando ao Redis...")
    
    with RedisSaver.from_conn_string(REDIS_URL) as checkpointer:
        checkpointer.setup()
        print("✅ Redis checkpointer configurado!")
        
        app = graph.compile(checkpointer=checkpointer)
        print("✅ Grafo compilado com Redis!\n")
        
        print("🧠" * 20)
        print("LANGGRAPH AGENT - TESTE DE MEMÓRIA COM REDIS")
        print("🧠" * 20)
        
        print("\n━" * 60)
        print("TESTE 1: Multi-turno (mesmo usuário)")
        print("━" * 60)
        
        THREAD_USER_42 = "user-42-sessao-1"
        
        run_agent(app, "Oi! Meu nome é Pedro.", THREAD_USER_42)
        input("\n[ENTER para continuar...]")
        
        run_agent(app, "Qual é o meu nome?", THREAD_USER_42)
        input("\n[ENTER para continuar...]")
        
        run_agent(app, "Busque as informações do usuário 42.", THREAD_USER_42)
        input("\n[ENTER para continuar...]")
        
        print("\n━" * 60)
        print("TESTE 2: Thread diferente (outro usuário)")
        print("━" * 60)
        
        THREAD_USER_99 = "user-99-sessao-1"
        run_agent(app, "Qual é o meu nome?", THREAD_USER_99)
        input("\n[ENTER para continuar...]")
        
        print("\n━" * 60)
        print("TESTE 3: Voltar ao user-42")
        print("━" * 60)
        
        run_agent(app, "Você ainda lembra meu nome?", THREAD_USER_42)
        
        print("\n" + "✅" * 20)
        print("TESTES CONCLUÍDOS!")
        print("✅" * 20)