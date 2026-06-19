# LangGraph + OpenAI Tool Calling Study

Projeto de estudo sobre construção de agentes de IA com LangGraph, OpenAI Tool Calling e Redis.

## O que este projeto cobre

- **Tool Calling**: Como o LLM decide qual função chamar e com quais argumentos
- **LangGraph**: Orquestração de agentes usando grafos de estado (ReAct Pattern)
- **Memória**: Persistência de conversas com MemorySaver e Redis
- **Redis**: Cache, histórico de chat e rate limiting

## Estrutura do Projeto
- langgraph_agent.py # Agente básico sem memória
- langgraph_agent_memory.py # Agente com MemorySaver (dev) 
- langgraph_agent_memory_redis.py # Agente com Redis (produção) 
- redis_example.py # Exemplos de uso do Redis 

### Padrão ReAct
- Thought → LLM raciocina sobre o que precisa fazer
- Action → LLM escolhe uma tool e argumentos
- Observation → Recebe o resultado da tool
- Repeat? → Precisa de mais info? Volta pro passo 1
- Answer → Responde ao usuário


### Redis
- `SETEX`: Cache com TTL (expiração automática)
- `RPUSH/LRANGE`: Listas para histórico de chat
- `INCR/EXPIRE`: Contadores para rate limiting

## Pré-requisitos

- Python 3.10+
- Redis Stack (para o checkpointer do LangGraph)
- Chave de API da OpenAI

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/PedroHMT/langgraph-langchain-redis-example.git
cd langgraph-langchain-redis-example

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env e adicionar OPENAI_API_KEY
