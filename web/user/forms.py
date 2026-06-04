from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Pet


class SignupForm(UserCreationForm):
    """회원가입에서 아이디, 이메일, 비밀번호를 받는 폼입니다."""

    # Django 기본 회원가입 폼에는 email이 필수가 아니어서 직접 필드를 추가했습니다.
    email = forms.EmailField(label='이메일', required=True)

    class Meta:
        # get_user_model()은 현재 프로젝트에서 사용하는 User 모델을 가져옵니다.
        model = get_user_model()
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': '아이디',
        }

    def __init__(self, *args, **kwargs):
        # 부모 클래스의 기본 설정을 먼저 불러온 뒤, 화면에 보일 라벨만 한글로 바꿉니다.
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = '비밀번호'
        self.fields['password2'].label = '비밀번호 확인'

    def clean_email(self):
        # clean_필드명 메서드는 해당 필드의 유효성 검사를 할 때 자동으로 호출됩니다.
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email


class ProfileForm(forms.ModelForm):
    """마이페이지에서 회원 이메일을 수정하는 폼입니다."""

    email = forms.EmailField(label='이메일', required=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email')
        labels = {
            'username': '아이디',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        # 아이디는 로그인 식별자로 쓰이므로 마이페이지에서는 수정하지 못하게 막았습니다.
        self.fields['username'].disabled = True

    def clean_email(self):
        email = self.cleaned_data['email']
        queryset = get_user_model().objects.filter(email=email)
        if self.user:
            # 자기 자신의 이메일은 중복으로 보지 않도록 제외합니다.
            queryset = queryset.exclude(pk=self.user.pk)
        if queryset.exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email


class PetForm(forms.ModelForm):
    """반려동물 등록/수정에 공통으로 사용하는 폼입니다."""

    class Meta:
        model = Pet
        fields = ('name', 'species', 'breed', 'age', 'gender', 'memo')
        labels = {
            'name': '이름',
            'species': '동물 종류',
            'breed': '품종',
            'age': '나이',
            'gender': '성별',
            'memo': '메모',
        }
        widgets = {
            'memo': forms.Textarea(attrs={'rows': 3, 'placeholder': '특징, 건강 상태, 좋아하는 것 등을 적어주세요.'}),
        }
