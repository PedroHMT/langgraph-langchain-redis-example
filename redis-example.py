import redis
import json
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
print(f"Ping Redis: {r.ping()}")

def search_data(user_id: int) -> dict:
    time.sleep(2)
    return {
        "id": user_id,
        "nome": f"user_{user_id}",
        "email": f"user{user_id}@example.com",
        "plano": "premium",
        "data_consulta": time.strftime("%H:%M:%S"),
    }

def get_user_cached(user_id: int, ttl_seconds: int = 3600) -> dict:
    cache_key = f"cache:user:{user_id}"

    cached = r.get(cache_key)

    if cached:
        return json.loads(cached)

    resultado = search_data(user_id)

    r.setex(cache_key, ttl_seconds, json.dumps(resultado))

    return resultado

def teste_cache():
    """Testa o cache com TTL."""
    print("=" * 50)
    print("CASO 1: Cache com TTL")
    print("=" * 50)
    
    user_id = 42
    
    print("\n🔍 Busca 1:")
    inicio = time.time()
    resultado = get_user_cached(user_id, ttl_seconds=10)
    print(f"   Resultado: {resultado}")
    print(f"   ⏱️  Tempo: {time.time() - inicio:.2f}s")
    
    print("\n🔍 Busca 2:")
    inicio = time.time()
    resultado = get_user_cached(user_id, ttl_seconds=10)
    print(f"   Resultado: {resultado}")
    print(f"   ⏱️  Tempo: {time.time() - inicio:.2f}s")
    
    print("\n🔍 Busca 3:")
    inicio = time.time()
    resultado = get_user_cached(user_id, ttl_seconds=10)
    print(f"   Resultado: {resultado}")
    print(f"   ⏱️  Tempo: {time.time() - inicio:.2f}s")
    
    # Esperar TTL expirar
    print("\n⏳ Esperando 11 segundos para o cache expirar...")
    time.sleep(11)
    
    inicio = time.time()
    resultado = get_user_cached(user_id, ttl_seconds=10)
    print(f"   Resultado: {resultado}")
    print(f"   ⏱️  Tempo: {time.time() - inicio:.2f}s")

# ============================================================
# CASO 2: Histórico de Conversa
# ============================================================

def add_message(session_id: str, role: str, content: str, ttl_seconds: int = 1800):
    """
    Adiciona uma mensagem ao histórico da sessão.
    TTL padrão: 30 minutos (1800s)
    """
    key = f"chat:{session_id}:messages"
    
    # Cria a mensagem como JSON
    message = json.dumps({"role": role, "content": content, "timestamp": time.time()})
    
    # Adiciona no final da lista (RPUSH)
    r.rpush(key, message)
    
    # Renova o TTL a cada mensagem (sessão ativa)
    r.expire(key, ttl_seconds)
    
    print(f"   📝 [{role}]: {content[:50]}...")


def get_history(session_id: str, limit: int = -1) -> list:
    """
    Retorna o histórico de mensagens da sessão.
    limit=-1 retorna todas, ou especifique um número para as últimas N.
    """
    key = f"chat:{session_id}:messages"
    
    if limit == -1:
        # Todas as mensagens
        messages = r.lrange(key, 0, -1)
    else:
        # Últimas N mensagens
        messages = r.lrange(key, -limit, -1)
    
    # Converte de JSON para dict
    return [json.loads(msg) for msg in messages]


def clear_history(session_id: str):
    """Limpa o histórico de uma sessão."""
    key = f"chat:{session_id}:messages"
    r.delete(key)
    print(f"   🗑️  Histórico da sessão {session_id} apagado.")


def teste_historico():
    """Testa o histórico de conversa."""
    print("\n" + "=" * 50)
    print("CASO 2: Histórico de Conversa")
    print("=" * 50)
    
    session_id = "user-42-sessao-1"
    
    # Limpar histórico anterior (para teste limpo)
    clear_history(session_id)
    
    # Simular uma conversa
    print("\n📨 Adicionando mensagens:")
    add_message(session_id, "user", "Oi! Meu nome é Pedro.")
    add_message(session_id, "assistant", "Olá Pedro! Como posso ajudar?")
    add_message(session_id, "user", "Qual o plano do usuário 42?")
    add_message(session_id, "assistant", "O usuário 42 tem plano premium.")
    add_message(session_id, "user", "Qual meu nome?")
    add_message(session_id, "assistant", "Seu nome é Pedro!")
    
    # Buscar histórico completo
    print("\n📜 Histórico completo:")
    historico = get_history(session_id)
    for i, msg in enumerate(historico, 1):
        print(f"   {i}. [{msg['role']}]: {msg['content']}")
    
    # Buscar apenas últimas 2 mensagens
    print("\n📜 Últimas 2 mensagens:")
    ultimas = get_history(session_id, limit=2)
    for msg in ultimas:
        print(f"   [{msg['role']}]: {msg['content']}")
    
    # Testar isolamento - outra sessão
    print("\n🔒 Testando isolamento (outra sessão):")
    session_id_2 = "user-99-sessao-1"
    clear_history(session_id_2)
    add_message(session_id_2, "user", "Oi, sou Maria!")
    
    print(f"\n   Histórico user-42: {len(get_history('user-42-sessao-1'))} mensagens")
    print(f"   Histórico user-99: {len(get_history('user-99-sessao-1'))} mensagens")
    print("   ✅ Sessões isoladas!")

# ============================================================
# CASO 3: Rate Limiting
# ============================================================

def check_rate_limit(user_id: str, limit: int = 5, window_seconds: int = 10) -> dict:
    """
    Verifica se o usuário pode fazer a requisição.
    
    Args:
        user_id: Identificador do usuário
        limit: Máximo de requisições permitidas
        window_seconds: Janela de tempo em segundos
    
    Returns:
        dict com: allowed (bool), current (int), limit (int), remaining (int)
    """
    key = f"rate:{user_id}"
    
    # Pipeline para executar INCR e EXPIRE atomicamente
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()
    
    current_count = results[0]  # Resultado do INCR
    
    allowed = current_count <= limit
    remaining = max(0, limit - current_count)
    
    return {
        "allowed": allowed,
        "current": current_count,
        "limit": limit,
        "remaining": remaining
    }


def simulate_request(user_id: str, request_num: int):
    """Simula uma requisição com rate limiting."""
    result = check_rate_limit(user_id, limit=5, window_seconds=10)
    
    if result["allowed"]:
        print(f"   ✅ Requisição {request_num}: PERMITIDA ({result['current']}/{result['limit']}) - Restam: {result['remaining']}")
    else:
        print(f"   ❌ Requisição {request_num}: BLOQUEADA ({result['current']}/{result['limit']}) - Rate limit excedido!")


def teste_rate_limiting():
    """Testa o rate limiting."""
    print("\n" + "=" * 50)
    print("CASO 3: Rate Limiting")
    print("=" * 50)
    
    user_id = "user-42"
    
    # Limpar contador anterior
    r.delete(f"rate:{user_id}")
    
    print(f"\n⚡ Simulando requisições (limite: 5 por 10 segundos)")
    print("-" * 40)
    
    # Fazer 8 requisições rapidamente
    print("\n📨 Rajada de 8 requisições:")
    for i in range(1, 9):
        simulate_request(user_id, i)
        time.sleep(0.1)  # Pequena pausa entre requisições
    
    # Esperar a janela resetar
    print("\n⏳ Esperando 10 segundos para a janela resetar...")
    time.sleep(10)
    
    # Novas requisições após reset
    print("\n📨 Novas requisições após reset:")
    for i in range(1, 4):
        simulate_request(user_id, i)
        time.sleep(0.1)
    
    print("\n✅ Rate limiting funcionando!")

if __name__ == "__main__":
    teste_cache()
    teste_historico()
    teste_rate_limiting()