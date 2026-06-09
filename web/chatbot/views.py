from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .conversation_state import filter_display_sources, serialize_sources, update_session_state
from .models import ChatMessage, ChatSession
from .rag_adapter import get_rag_response
from .shelter_recommendation import append_shelter_links_for_recommendation


WELCOME_MESSAGE = '안녕하세요. 반려견 케어, 견종 검색, 견종 추천에 대해 질문해 주세요.'


def _session_title(question):
    return question[:36] if len(question) <= 36 else f'{question[:36]}...'


def _intent_from_analysis(analysis):
    topics = list(getattr(analysis, 'topics', []) or [])
    if 'breed_recommendation' in topics:
        return '견종 추천'
    return '일반 상담'


def _build_fallback_reply(error):
    return {
        'answer': (
            '현재 RAG 답변 생성 중 오류가 발생했습니다. '
            '잠시 후 다시 시도해 주세요.\n\n'
            f'오류 확인용 메시지: {error}'
        ),
        'intent': '오류',
        'analysis': None,
        'sources': [],
    }


def build_reply(message, request=None):
    """Generate a chatbot reply through the backend RAG workflow."""

    try:
        rag_response = get_rag_response(message)
    except Exception as error:
        return _build_fallback_reply(error)

    analysis = rag_response.analysis
    display_sources = filter_display_sources(
        question=message,
        sources=rag_response.sources,
        analysis=analysis,
    )
    sources = serialize_sources(display_sources)
    answer = append_shelter_links_for_recommendation(
        question=message,
        answer=rag_response.answer,
        analysis=analysis,
        base_url=request.build_absolute_uri('/') if request else None,
    )

    return {
        'answer': answer,
        'intent': _intent_from_analysis(analysis),
        'analysis': analysis,
        'sources': sources,
    }


def chat(request):
    """Render the chatbot page and persist chat messages."""

    pinned_sessions = ChatSession.objects.none()
    unpinned_sessions = ChatSession.objects.none()
    active_session = None

    if request.user.is_authenticated:
        all_sessions = ChatSession.objects.filter(user=request.user)
        pinned_sessions = all_sessions.filter(is_pinned=True)
        unpinned_sessions = all_sessions.filter(is_pinned=False)
        session_id = request.GET.get('session')
        if session_id:
            active_session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == 'POST':
        question = request.POST.get('message', '').strip()
        posted_session_id = request.POST.get('session_id')

        if question:
            reply = build_reply(question, request=request)

            if request.user.is_authenticated:
                if posted_session_id:
                    active_session = get_object_or_404(ChatSession, id=posted_session_id, user=request.user)
                else:
                    active_session = ChatSession.objects.create(user=request.user, title=_session_title(question))

                if active_session.title == '새 대화':
                    active_session.title = _session_title(question)
                    active_session.save(update_fields=['title', 'updated_at'])

                ChatMessage.objects.create(session=active_session, role='user', content=question)
                assistant_message = ChatMessage.objects.create(
                    session=active_session,
                    role='assistant',
                    content=reply['answer'],
                    intent=reply['intent'],
                    sources=reply['sources'],
                )
                update_session_state(
                    session=active_session,
                    question=question,
                    answer=reply['answer'],
                    analysis=reply['analysis'],
                    assistant_message=assistant_message,
                    sources=reply['sources'],
                )
                return redirect(f'{request.path}?session={active_session.id}')

            anonymous_messages = request.session.get(
                'anonymous_chat_messages',
                [{'role': 'assistant', 'content': WELCOME_MESSAGE, 'sources': []}],
            )
            anonymous_messages.extend(
                [
                    {'role': 'user', 'content': question, 'sources': []},
                    {
                        'role': 'assistant',
                        'content': reply['answer'],
                        'intent': reply['intent'],
                        'sources': reply['sources'],
                    },
                ]
            )
            request.session['anonymous_chat_messages'] = anonymous_messages
            request.session.modified = True
            return redirect(request.path)

    if request.user.is_authenticated and active_session:
        messages = active_session.messages.all()
    elif request.user.is_authenticated:
        messages = [{'role': 'assistant', 'content': WELCOME_MESSAGE, 'sources': []}]
    else:
        messages = request.session.get(
            'anonymous_chat_messages',
            [{'role': 'assistant', 'content': WELCOME_MESSAGE, 'sources': []}],
        )

    return render(
        request,
        'chatbot/chat.html',
        {
            'messages': messages,
            'pinned_sessions': pinned_sessions,
            'unpinned_sessions': unpinned_sessions,
            'active_session': active_session,
        },
    )
@require_POST
@login_required
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()
    return redirect('chatbot:chat')

@require_POST
def clear_anonymous_chat(request):
    if 'anonymous_chat_messages' in request.session:
        del request.session['anonymous_chat_messages']
        request.session.modified = True
    return redirect('chatbot:chat')

@require_POST
@login_required
def toggle_pin(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.is_pinned = not session.is_pinned
    session.save(update_fields=['is_pinned'])
    
    active_session_id = request.GET.get('active_session')
    if active_session_id:
        return redirect(f"/chatbot/?session={active_session_id}")
    return redirect(f"/chatbot/?session={session.id}")

@require_POST
def api_chat(request):
    question = request.POST.get('message', '').strip()
    posted_session_id = request.POST.get('session_id')
    
    if not question:
        return JsonResponse({"status": "error", "message": "Message is empty"}, status=400)
        
    reply = build_reply(question)
    
    if request.user.is_authenticated:
        if posted_session_id:
            active_session = get_object_or_404(ChatSession, id=posted_session_id, user=request.user)
        else:
            active_session = ChatSession.objects.create(user=request.user, title=_session_title(question))
            
        if active_session.title == '새 대화':
            active_session.title = _session_title(question)
            active_session.save(update_fields=['title', 'updated_at'])
            
        ChatMessage.objects.create(session=active_session, role='user', content=question)
        assistant_message = ChatMessage.objects.create(
            session=active_session,
            role='assistant',
            content=reply['answer'],
            intent=reply['intent'],
            sources=reply['sources'],
        )
        update_session_state(
            session=active_session,
            question=question,
            answer=reply['answer'],
            analysis=reply['analysis'],
            assistant_message=assistant_message,
            sources=reply['sources'],
        )
        return JsonResponse({
            "status": "success",
            "session_id": active_session.id,
            "session_title": active_session.title,
            "answer": reply['answer'],
            "intent": reply['intent'],
            "sources": reply['sources'],
        })
    else:
        anonymous_messages = request.session.get(
            'anonymous_chat_messages',
            [{'role': 'assistant', 'content': WELCOME_MESSAGE, 'sources': []}],
        )
        anonymous_messages.extend([
            {'role': 'user', 'content': question, 'sources': []},
            {
                'role': 'assistant',
                'content': reply['answer'],
                'intent': reply['intent'],
                'sources': reply['sources'],
            },
        ])
        request.session['anonymous_chat_messages'] = anonymous_messages
        request.session.modified = True
        return JsonResponse({
            "status": "success",
            "session_id": None,
            "answer": reply['answer'],
            "intent": reply['intent'],
            "sources": reply['sources'],
        })
