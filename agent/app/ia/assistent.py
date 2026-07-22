from app.ai.llm.client import (
    LLMClient
)

from app.ai.memory.memory import (
    Memory
)


SYSTEM_PROMPT = """
Você é um assistente de IA especializado
em infraestrutura de TI.

Você pode ajudar com:

- Linux
- Ubuntu
- Docker
- redes
- VPN
- servidores
- monitoramento
- Prometheus
- Grafana
- bancos de dados
- infraestrutura

Você deve:

1. Responder com precisão.
2. Não inventar informações.
3. Utilizar ferramentas quando disponíveis.
4. Nunca executar comandos perigosos
   sem autorização explícita.
5. Explicar ações antes de executá-las.
"""


class AIAssistant:

    def __init__(self):

        self.llm = LLMClient()

        self.memory = Memory()

    async def chat(
        self,
        message: str,
        session_id: str
    ):

        history = await (
            self.memory.get_history(
                session_id
            )
        )

        messages = [

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }

        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": message
            }
        )

        response = await (
            self.llm.chat(
                messages
            )
        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

        await self.memory.save_message(
            session_id,
            "user",
            message
        )

        await self.memory.save_message(
            session_id,
            "assistant",
            answer
        )

        return answer
