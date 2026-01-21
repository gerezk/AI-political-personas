import chainlit as cl
from chainlit.input_widget import Select
import ollama

# Initialize the async client
client = ollama.AsyncClient()


@cl.on_chat_start
async def start():
    # avatar files names are the same as agent['name'] in lowercase with space replaced by _:
    # - public/avatars/republican.png
    # - public/avatars/democrat.png

    # Initialize the transcript and settings
    cl.user_session.set("transcript", [])

    settings = await cl.ChatSettings([
        Select(
            id="Persona",
            label="Who should answer?",
            values=["Republican", "Democrat", "Both"],
            initial_index=2
        )
    ]).send()
    cl.user_session.set("settings", settings)

    await cl.Message(content="Welcome to Politikai! History is being recorded.").send()

@cl.on_message
async def main(message: cl.Message):
    # Clear the sidebar from the previous turn
    await cl.ElementSidebar.set_elements([])

    transcript = cl.user_session.get("transcript")
    settings = cl.user_session.get("settings")
    persona_choice = settings.get("Persona")

    # 1. Add user message to history
    transcript.append({"role": "user", "content": message.content})

    agents_to_run = []
    if persona_choice in ["Democrat", "Both"]:
        agents_to_run.append({"name": "Democrat", "model": "dem-model:latest"})
    if persona_choice in ["Republican", "Both"]:
        agents_to_run.append({"name": "Republican", "model": "rep-model:latest"})

    # Store the current turn's responses here to pass to the Fact Checker
    current_turn_responses = []

    # 2. Sequential execution of models
    for i, agent in enumerate(agents_to_run):
        # The author parameter will automatically use the matching avatar
        # from public/avatars/{author}.png
        agent_msg = cl.Message(content=f"{agent['name']}: ", author=agent["name"])
        await agent_msg.send()

        # If this is NOT the first agent, nudge the model
        current_context = list(transcript)
        if i > 0:
            current_context.append({
                "role": "user",
                "content": message.content,
            })

        full_response = ""
        try:
            stream = await client.chat(
                model=agent["model"],
                messages=current_context,
                stream=True,
                keep_alive=0
            )

            async for chunk in stream:
                token = chunk.get('message', {}).get('content', '')
                if token:
                    full_response += token
                    await agent_msg.stream_token(token)

            # pass current response to fact-checker
            current_turn_responses.append(full_response)

            # Update message with final content
            if not full_response:
                agent_msg.content = "*Chose to remain silent.*"
            await agent_msg.update()

            # Save the response to the transcript
            transcript.append({"role": "assistant", "author": agent["name"], "content": full_response})

        except Exception as e:
            await cl.Message(content=f"Error with {agent['name']}: {str(e)}", author="System").send()

    # 3. SIDE PANEL: Fact Checker (Stateless)
    if current_turn_responses:
        # Create a condensed prompt of only what was just said
        fact_check_prompt = (f"Analyze the following debate statement or statements for factual accuracy and logical "
                             f"fallacies. Be objective and brief:\n\n{current_turn_responses}")

        try:
            # Use client.chat() instead of client.generate()
            # The fact checker gets NO conversation history (stateless)
            response = await client.chat(
                model='fact-checker:latest',
                messages=[{"role": "user", "content": fact_check_prompt}],
                stream=False,
                keep_alive=0
            )

            fact_check_content = response['message']['content']
            separators = ["FACT CHECKER RESPONSE", "Fact Checker Response"]
            if separators[0] in fact_check_content:
                separator = separators[0]
            else:
                separator = separators[1]
            fact_check_response = fact_check_content.split(separator, 1)[1][3:] # [3:] ignores ** at the beginning
            fact_check_response = fact_check_response.replace('"','') # strip " from beginning and end of content

            # Use ElementSidebar instead of display="side"
            await cl.ElementSidebar.set_title("Fact Check Analysis")
            await cl.ElementSidebar.set_elements([
                cl.Text(
                    name="Fact Checker",
                    content=fact_check_response
                )
            ])

        except Exception as e:
            print(f"Fact Checker Error: {e}")

    cl.user_session.set("transcript", transcript)

@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)