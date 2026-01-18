# -*- coding: utf-8 -*-
"""Flask backend for Political Debate Fact-Checker"""

from flask import Flask, render_template, request, jsonify, Response
import ollama
import json
import time
import uuid

app = Flask(__name__)

# Model configuration
DEMOCRAT_MODEL = 'nadinekitzwoegerer/dem-model:v2'
REPUBLICAN_MODEL = 'nadinekitzwoegerer/rep-model:v2'
FACTCHECK_MODEL = 'group5/fact-checker-mistral:v1'

# In-memory conversation storage (per session)
conversations = {}


def get_or_create_conversation(session_id: str) -> dict:
    """Get existing conversation or create a new one."""
    if session_id not in conversations:
        conversations[session_id] = {
            'democrat_history': [],
            'republican_history': [],
            'turns': []  # Store all Q&A turns for display
        }
    return conversations[session_id]


def get_model_response(model: str, messages: list) -> str:
    """Get response from an Ollama model with conversation history."""
    response = ollama.chat(
        model=model,
        messages=messages
    )
    return response['message']['content']


def fact_check(user_text: str, dem_text: str, rep_text: str) -> dict:
    """Run fact-checking on both responses."""
    fc_prompt = f"""FACTCHECK_TURN
User: {user_text}

DEM answer:
{dem_text}

REP answer:
{rep_text}

Return JSON with fields: results (per origin) and moderator_message.
Only include factual, checkable claims. Exclude policy proposals/opinions.
If unverifiable without sources, use UNVERIFIABLE_WITHOUT_SOURCES and list what_to_verify.
"""
    print(f"[DEBUG FACTCHECK] Prompt sent to fact-checker:")
    print(f"[DEBUG FACTCHECK] {fc_prompt[:500]}...")

    response = ollama.chat(
        model=FACTCHECK_MODEL,
        messages=[{'role': 'user', 'content': fc_prompt}],
        format='json'
    )

    raw_response = response['message']['content']
    print(f"[DEBUG FACTCHECK] Raw response: {raw_response}")

    result = json.loads(raw_response)
    print(f"[DEBUG FACTCHECK] Parsed result keys: {result.keys()}")

    return result


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/debate', methods=['POST'])
def run_debate():
    """Run a full debate turn with fact-checking and conversation memory."""
    data = request.get_json()
    question = data.get('question', '')
    session_id = data.get('session_id', str(uuid.uuid4()))

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    try:
        # Get or create conversation
        conv = get_or_create_conversation(session_id)

        # Add user question to both histories
        conv['democrat_history'].append({'role': 'user', 'content': question})
        conv['republican_history'].append({'role': 'user', 'content': question})

        # DEBUG: Log history lengths
        print(f"[DEBUG] Session: {session_id}")
        print(f"[DEBUG] Democrat history length: {len(conv['democrat_history'])}")
        print(f"[DEBUG] Republican history length: {len(conv['republican_history'])}")
        print(f"[DEBUG] Republican history: {conv['republican_history']}")

        # Get Democrat response with full history
        dem_text = get_model_response(DEMOCRAT_MODEL, conv['democrat_history'])
        conv['democrat_history'].append({'role': 'assistant', 'content': dem_text})

        # Get Republican response with full history
        rep_text = get_model_response(REPUBLICAN_MODEL, conv['republican_history'])
        conv['republican_history'].append({'role': 'assistant', 'content': rep_text})

        print(f"[DEBUG] Republican response: {rep_text[:100]}...")

        # Fact-check both responses
        fact_check_result = fact_check(question, dem_text, rep_text)

        # Store this turn
        turn = {
            'question': question,
            'democrat': dem_text,
            'republican': rep_text,
            'fact_check': fact_check_result
        }
        conv['turns'].append(turn)

        return jsonify({
            'session_id': session_id,
            'question': question,
            'democrat': dem_text,
            'republican': rep_text,
            'fact_check': fact_check_result,
            'turn_number': len(conv['turns'])
        })

    except Exception as e:
        import traceback
        print(f"[ERROR] {str(e)}")
        print(f"[ERROR TRACEBACK] {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debate/stream', methods=['POST'])
def run_debate_stream():
    """Run a debate turn with Server-Sent Events for real-time updates."""
    data = request.get_json()
    question = data.get('question', '')

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    def generate():
        try:
            # Signal start
            yield f"data: {json.dumps({'status': 'started', 'step': 'democrat'})}\n\n"

            # Get Democrat response
            dem_text = get_model_response(DEMOCRAT_MODEL, question)
            yield f"data: {json.dumps({'status': 'progress', 'step': 'democrat', 'content': dem_text})}\n\n"

            # Get Republican response
            yield f"data: {json.dumps({'status': 'progress', 'step': 'republican_start'})}\n\n"
            rep_text = get_model_response(REPUBLICAN_MODEL, question)
            yield f"data: {json.dumps({'status': 'progress', 'step': 'republican', 'content': rep_text})}\n\n"

            # Fact-check
            yield f"data: {json.dumps({'status': 'progress', 'step': 'factcheck_start'})}\n\n"
            fact_check_result = fact_check(question, dem_text, rep_text)
            yield f"data: {json.dumps({'status': 'complete', 'fact_check': fact_check_result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/conversation/reset', methods=['POST'])
def reset_conversation():
    """Reset the conversation history for a session."""
    data = request.get_json()
    session_id = data.get('session_id', '')

    if session_id and session_id in conversations:
        del conversations[session_id]

    return jsonify({'status': 'ok', 'message': 'Conversation reset'})


@app.route('/api/conversation/history', methods=['POST'])
def get_history():
    """Get the conversation history for a session."""
    data = request.get_json()
    session_id = data.get('session_id', '')

    if not session_id or session_id not in conversations:
        return jsonify({'turns': []})

    return jsonify({'turns': conversations[session_id]['turns']})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
