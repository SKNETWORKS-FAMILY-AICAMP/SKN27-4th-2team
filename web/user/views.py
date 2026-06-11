from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import PetForm, ProfileForm, SignupForm
from .models import Pet


class UserLoginView(LoginView):
    """Django 기본 로그인 기능에 우리가 만든 로그인 템플릿을 연결합니다."""

    template_name = 'user/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """Django 기본 로그아웃 기능을 그대로 사용합니다."""

    pass


class UserSignupView(CreateView):
    """회원가입 화면과 저장 로직을 담당합니다."""

    form_class = SignupForm
    template_name = 'user/signup.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        # 회원가입에 성공하면 새로 만든 계정으로 바로 로그인시킵니다.
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserProfileView(UpdateView):
    """마이페이지에서 사용자 이메일을 수정하고 반려동물 목록을 보여줍니다."""

    form_class = ProfileForm
    template_name = 'user/profile.html'
    success_url = reverse_lazy('user:profile')

    def get_object(self, queryset=None):
        # UpdateView는 수정할 객체가 필요한데, 여기서는 현재 로그인한 사용자가 대상입니다.
        return self.request.user

    def dispatch(self, request, *args, **kwargs):
        # 로그인하지 않은 사용자가 마이페이지에 들어오면 로그인 페이지로 보냅니다.
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=reverse_lazy('user:login'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # 템플릿에서 회원 정보 폼 외에 반려동물 등록 폼과 목록도 같이 사용하기 위해 추가합니다.
        context = super().get_context_data(**kwargs)
        context['pet_form'] = PetForm()
        context['pets'] = self.request.user.pets.all()
        # 과거 퀴즈(테스트) 결과 목록 전달
        context['test_results'] = self.request.user.test_results.all()
        # 견종 및 유기견 즐겨찾기 목록 전달
        context['dog_favorites'] = self.request.user.dog_favorites.all()
        context['shelter_favorites'] = self.request.user.shelter_favorites.all()
        return context


@login_required
def create_pet(request):
    """마이페이지에서 새 반려동물을 등록합니다."""

    if request.method == 'POST':
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            # 어떤 사용자의 반려동물인지 연결한 뒤 저장합니다.
            pet.user = request.user
            pet.save()
    return redirect('user:profile')


@login_required
def delete_pet(request, pet_id):
    """마이페이지에서 반려동물을 삭제합니다."""

    if request.method == 'POST':
        # id만으로 찾지 않고 user 조건도 함께 걸어, 남의 반려동물을 삭제하지 못하게 합니다.
        pet = get_object_or_404(Pet, id=pet_id, user=request.user)
        pet.delete()
    return redirect('user:profile')


@login_required
def update_pet(request, pet_id):
    """등록한 반려동물 정보를 수정합니다."""

    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    if request.method == 'POST':
        form = PetForm(request.POST, instance=pet)
        if form.is_valid():
            form.save()
            return redirect('user:profile')
    else:
        # GET 요청일 때는 기존 반려동물 정보가 채워진 폼을 보여줍니다.
        form = PetForm(instance=pet)

    return render(request, 'user/pet_form.html', {'form': form, 'pet': pet})
