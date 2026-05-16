"""
Utility functions per django-ratelimit
SECURITY: Gestione IP reale dietro Cloudflare/Render proxy
"""

def get_real_ip_for_ratelimit(group, request):
    """
    Estrae IP reale del client dietro Cloudflare e Render proxy.

    Priorità:
    1. CF-Connecting-IP (Cloudflare, più affidabile)
    2. X-Forwarded-For primo IP (Render/generic proxy)
    3. REMOTE_ADDR (fallback dev locale)

    Args:
        group: Nome del gruppo rate limit (non usato)
        request: Django HttpRequest object

    Returns:
        str: IP address del client reale
    """
    # Cloudflare passa CF-Connecting-IP con IP reale client
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip.strip()

    # X-Forwarded-For può contenere chain: "client, proxy1, proxy2"
    # Prendiamo il primo (client reale)
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()

    # Fallback: IP diretto (sviluppo locale senza proxy)
    return request.META.get('REMOTE_ADDR', '0.0.0.0')
