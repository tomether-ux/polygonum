"""
Custom authentication backend per supportare login con username o email
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Permette agli utenti di effettuare il login usando username o email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # Cerca l'utente per username O email
            user = User.objects.get(Q(username=username) | Q(email=username))

            # Verifica la password
            if user.check_password(password):
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
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass
            return None

        return None
