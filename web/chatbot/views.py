from django.shortcuts import get_object_or_404, redirect, render

from .models import ChatMessage, ChatSession


WELCOME_MESSAGE = '안녕하세요. 반려견 케어, 견종 검색, 입양 준비에 대해 질문해 주세요.'


def classify_intent(message):
    """사용자 질문을 아주 단순한 키워드 방식으로 분류합니다."""

    if any(keyword in message for keyword in ['추천', '어울', '맞는 견종']):
        return '견종 추천'
    if any(keyword in message for keyword in ['견종', '말티즈', '푸들', '리트리버']):
        return '견종 검색'
    if any(keyword in message for keyword in ['입양', '준비', '테스트']):
        return '입양 준비'
    if any(keyword in message for keyword in ['초보', '가이드', '훈련', '배변', '산책']):
        return '초보 보호자 가이드'
    return '일반 상담'


def build_reply(message):
    """현재는 임시 답변을 만들고, 나중에 이 부분에 RAG/LLM을 연결하면 됩니다."""

    intent = classify_intent(message)
    return {
        'intent': intent,
        'answer': (
            f'현재 질문은 "{intent}" 유형으로 분류했습니다. '
            '아직 데이터와 RAG는 연결 전이라 임시 답변을 보여주고 있으며, '
            '이 영역에 나중에 VectorDB 검색 결과와 LLM 답변을 연결할 수 있습니다.'
        ),
    }


def _session_title(question):
    """채팅 내역에 표시할 제목을 질문 앞부분으로 만듭니다."""

    return question[:36] if len(question) <= 36 else f'{question[:36]}...'


def chat(request):
    """챗봇 화면을 보여주고, 질문이 들어오면 답변과 채팅 내역을 저장합니다."""

    sessions = ChatSession.objects.none()
    active_session = None

    if request.user.is_authenticated:
        # 로그인 사용자는 DB에 저장된 본인의 채팅 내역을 볼 수 있습니다.
        sessions = ChatSession.objects.filter(user=request.user)
        session_id = request.GET.get('session')
        if session_id:
            active_session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == 'POST':
        question = request.POST.get('message', '').strip()
        posted_session_id = request.POST.get('session_id')

        if question:
            reply = build_reply(question)

            if request.user.is_authenticated:
                # 기존 대화방에서 질문한 경우에는 그 대화방에 이어서 저장합니다.
                if posted_session_id:
                    active_session = get_object_or_404(ChatSession, id=posted_session_id, user=request.user)
                else:
                    active_session = ChatSession.objects.create(user=request.user, title=_session_title(question))

                if active_session.title == '새 대화':
                    active_session.title = _session_title(question)
                    active_session.save(update_fields=['title', 'updated_at'])

                ChatMessage.objects.create(session=active_session, role='user', content=question)
                ChatMessage.objects.create(
                    session=active_session,
                    role='assistant',
                    content=reply['answer'],
                    intent=reply['intent'],
                )
                return redirect(f'{request.path}?session={active_session.id}')

            # 비로그인 사용자는 DB 저장 없이 현재 브라우저 세션에만 임시로 보관합니다.
            request.session['anonymous_chat_messages'] = [
                {'role': 'assistant', 'content': WELCOME_MESSAGE},
                {'role': 'user', 'content': question},
                {
                    'role': 'assistant',
                    'content': reply['answer'],
                    'intent': reply['intent'],
                },
            ]
            request.session.modified = True
            return redirect(request.path)

    if request.user.is_authenticated and active_session:
        messages = active_session.messages.all()
    elif request.user.is_authenticated:
        messages = [{'role': 'assistant', 'content': WELCOME_MESSAGE}]
    else:
        messages = request.session.get(
            'anonymous_chat_messages',
            [{'role': 'assistant', 'content': WELCOME_MESSAGE}],
        )

    return render(
        request,
        'chatbot/chat.html',
        {
            'messages': messages,
            'sessions': sessions,
            'active_session': active_session,
        },
    )
