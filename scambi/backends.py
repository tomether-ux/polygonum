"""
Custom authentication backend per supportare login con username o email
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Permette agli utenti di effettuare il login usando username o email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # L'email non è case-sensitive; select_related evita una query
            # aggiuntiva quando controlliamo ban e sospensione.
            user = User.objects.select_related('userprofile').get(
                Q(username=username) | Q(email__iexact=username)
            )

            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            # Esegui un check password anche se l'utente non esiste
            # per evitare timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Se ci sono più utenti con la stessa email (non dovrebbe succedere)
            # proviamo prima con username esatto
            try:
                user = User.objects.select_related('userprofile').get(username=username)
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
            except User.DoesNotExist:
                pass
            return None

        return None

    def user_can_authenticate(self, user):
        """Applica in un solo punto stato Django, ban e sospensioni."""
        if not super().user_can_authenticate(user):
            return False

        try:
            profile = user.userprofile
        except User.userprofile.RelatedObjectDoesNotExist:
            # Gli account legacy senza profilo devono poter accedere alla pagina
            # che consente di completarlo.
            return True

        if profile.is_banned:
            return False

        if profile.suspension_until and profile.suspension_until > timezone.now():
            return False

        return True

    def get_user(self, user_id):
        """Controlla le restrizioni anche per sessioni create in precedenza."""
        try:
            user = User.objects.select_related('userprofile').get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
