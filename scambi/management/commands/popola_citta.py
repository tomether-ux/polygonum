from django.core.management.base import BaseCommand
from scambi.models import Citta, DistanzaCitta
import math


class Command(BaseCommand):
    help = 'Popola il database con tutte le 110 province italiane e calcola le distanze'

    def handle(self, *args, **options):
        self.stdout.write("🇮🇹 Popolamento province italiane...")

        # Lista completa delle 110 province italiane (capoluoghi) con coordinate
        # Formato: (nome, provincia_sigla, regione, latitudine, longitudine)
        province = [
            # Abruzzo
            ("L'Aquila", "AQ", "Abruzzo", 42.3498, 13.3995),
            ("Chieti", "CH", "Abruzzo", 42.3515, 14.1647),
            ("Pescara", "PE", "Abruzzo", 42.4618, 14.2136),
            ("Teramo", "TE", "Abruzzo", 42.6589, 13.7040),

            # Basilicata
            ("Potenza", "PZ", "Basilicata", 40.6389, 15.8050),
            ("Matera", "MT", "Basilicata", 40.6664, 16.6043),

            # Calabria
            ("Catanzaro", "CZ", "Calabria", 38.9098, 16.5877),
            ("Cosenza", "CS", "Calabria", 39.2987, 16.2514),
            ("Crotone", "KR", "Calabria", 39.0804, 17.1251),
            ("Reggio Calabria", "RC", "Calabria", 38.1113, 15.6476),
            ("Vibo Valentia", "VV", "Calabria", 38.6759, 16.1003),

            # Campania
            ("Napoli", "NA", "Campania", 40.8518, 14.2681),
            ("Avellino", "AV", "Campania", 40.9142, 14.7906),
            ("Benevento", "BN", "Campania", 41.1297, 14.7826),
            ("Caserta", "CE", "Campania", 41.0732, 14.3335),
            ("Salerno", "SA", "Campania", 40.6824, 14.7681),

            # Emilia-Romagna
            ("Bologna", "BO", "Emilia-Romagna", 44.4949, 11.3426),
            ("Ferrara", "FE", "Emilia-Romagna", 44.8381, 11.6198),
            ("Forlì-Cesena", "FC", "Emilia-Romagna", 44.2229, 12.0403),
            ("Modena", "MO", "Emilia-Romagna", 44.6471, 10.9252),
            ("Parma", "PR", "Emilia-Romagna", 44.8015, 10.3279),
            ("Piacenza", "PC", "Emilia-Romagna", 45.0526, 9.6924),
            ("Ravenna", "RA", "Emilia-Romagna", 44.4184, 12.2035),
            ("Reggio Emilia", "RE", "Emilia-Romagna", 44.6989, 10.6297),
            ("Rimini", "RN", "Emilia-Romagna", 44.0678, 12.5695),

            # Friuli-Venezia Giulia
            ("Trieste", "TS", "Friuli-Venezia Giulia", 45.6495, 13.7768),
            ("Gorizia", "GO", "Friuli-Venezia Giulia", 45.9411, 13.6222),
            ("Pordenone", "PN", "Friuli-Venezia Giulia", 45.9636, 12.6594),
            ("Udine", "UD", "Friuli-Venezia Giulia", 46.0710, 13.2345),

            # Lazio
            ("Roma", "RM", "Lazio", 41.9028, 12.4964),
            ("Frosinone", "FR", "Lazio", 41.6396, 13.3508),
            ("Latina", "LT", "Lazio", 41.4677, 12.9037),
            ("Rieti", "RI", "Lazio", 42.4048, 12.8566),
            ("Viterbo", "VT", "Lazio", 42.4174, 12.1084),

            # Liguria
            ("Genova", "GE", "Liguria", 44.4056, 8.9463),
            ("Imperia", "IM", "Liguria", 43.8868, 8.0270),
            ("La Spezia", "SP", "Liguria", 44.1025, 9.8246),
            ("Savona", "SV", "Liguria", 44.3075, 8.4818),

            # Lombardia
            ("Milano", "MI", "Lombardia", 45.4642, 9.1900),
            ("Bergamo", "BG", "Lombardia", 45.6983, 9.6773),
            ("Brescia", "BS", "Lombardia", 45.5416, 10.2118),
            ("Como", "CO", "Lombardia", 45.8081, 9.0852),
            ("Cremona", "CR", "Lombardia", 45.1333, 10.0226),
            ("Lecco", "LC", "Lombardia", 45.8564, 9.3985),
            ("Lodi", "LO", "Lombardia", 45.3142, 9.5034),
            ("Mantova", "MN", "Lombardia", 45.1564, 10.7914),
            ("Monza e Brianza", "MB", "Lombardia", 45.5845, 9.2744),
            ("Pavia", "PV", "Lombardia", 45.1847, 9.1582),
            ("Sondrio", "SO", "Lombardia", 46.1699, 9.8782),
            ("Varese", "VA", "Lombardia", 45.8206, 8.8250),

            # Marche
            ("Ancona", "AN", "Marche", 43.6158, 13.5189),
            ("Ascoli Piceno", "AP", "Marche", 42.8534, 13.5759),
            ("Fermo", "FM", "Marche", 43.1605, 13.7188),
            ("Macerata", "MC", "Marche", 43.3002, 13.4532),
            ("Pesaro e Urbino", "PU", "Marche", 43.9103, 12.9130),

            # Molise
            ("Campobasso", "CB", "Molise", 41.5630, 14.6560),
            ("Isernia", "IS", "Molise", 41.5896, 14.2343),

            # Piemonte
            ("Torino", "TO", "Piemonte", 45.0703, 7.6869),
            ("Alessandria", "AL", "Piemonte", 44.9137, 8.6151),
            ("Asti", "AT", "Piemonte", 44.9009, 8.2065),
            ("Biella", "BI", "Piemonte", 45.5629, 8.0581),
            ("Cuneo", "CN", "Piemonte", 44.3841, 7.5420),
            ("Novara", "NO", "Piemonte", 45.4469, 8.6218),
            ("Verbano-Cusio-Ossola", "VB", "Piemonte", 45.9214, 8.5512),
            ("Vercelli", "VC", "Piemonte", 45.3204, 8.4184),

            # Puglia
            ("Bari", "BA", "Puglia", 41.1171, 16.8719),
            ("Barletta-Andria-Trani", "BT", "Puglia", 41.3205, 16.2857),
            ("Brindisi", "BR", "Puglia", 40.6327, 17.9461),
            ("Foggia", "FG", "Puglia", 41.4621, 15.5444),
            ("Lecce", "LE", "Puglia", 40.3515, 18.1750),
            ("Taranto", "TA", "Puglia", 40.4762, 17.2303),

            # Sardegna
            ("Cagliari", "CA", "Sardegna", 39.2238, 9.1217),
            ("Nuoro", "NU", "Sardegna", 40.3213, 9.3300),
            ("Oristano", "OR", "Sardegna", 39.9037, 8.5912),
            ("Sassari", "SS", "Sardegna", 40.7259, 8.5590),
            ("Sud Sardegna", "SU", "Sardegna", 39.1643, 8.5591),

            # Sicilia
            ("Palermo", "PA", "Sicilia", 38.1157, 13.3615),
            ("Agrigento", "AG", "Sicilia", 37.3112, 13.5765),
            ("Caltanissetta", "CL", "Sicilia", 37.4902, 14.0622),
            ("Catania", "CT", "Sicilia", 37.5079, 15.0830),
            ("Enna", "EN", "Sicilia", 37.5671, 14.2794),
            ("Messina", "ME", "Sicilia", 38.1937, 15.5542),
            ("Ragusa", "RG", "Sicilia", 36.9268, 14.7255),
            ("Siracusa", "SR", "Sicilia", 37.0755, 15.2866),
            ("Trapani", "TP", "Sicilia", 38.0176, 12.5365),

            # Toscana
            ("Firenze", "FI", "Toscana", 43.7696, 11.2558),
            ("Arezzo", "AR", "Toscana", 43.4632, 11.8796),
            ("Grosseto", "GR", "Toscana", 42.7631, 11.1136),
            ("Livorno", "LI", "Toscana", 43.5485, 10.3106),
            ("Lucca", "LU", "Toscana", 43.8376, 10.4950),
            ("Massa-Carrara", "MS", "Toscana", 44.0366, 10.1411),
            ("Pisa", "PI", "Toscana", 43.7228, 10.4017),
            ("Pistoia", "PT", "Toscana", 43.9330, 10.9177),
            ("Prato", "PO", "Toscana", 43.8777, 11.1021),
            ("Siena", "SI", "Toscana", 43.3188, 11.3308),

            # Trentino-Alto Adige
            ("Trento", "TN", "Trentino-Alto Adige", 46.0664, 11.1257),
            ("Bolzano", "BZ", "Trentino-Alto Adige", 46.4983, 11.3548),

            # Umbria
            ("Perugia", "PG", "Umbria", 43.1107, 12.3908),
            ("Terni", "TR", "Umbria", 42.5635, 12.6450),

            # Valle d'Aosta
            ("Aosta", "AO", "Valle d'Aosta", 45.7383, 7.3206),

            # Veneto
            ("Venezia", "VE", "Veneto", 45.4408, 12.3155),
            ("Belluno", "BL", "Veneto", 46.1428, 12.2168),
            ("Padova", "PD", "Veneto", 45.4064, 11.8768),
            ("Rovigo", "RO", "Veneto", 45.0705, 11.7904),
            ("Treviso", "TV", "Veneto", 45.6669, 12.2430),
            ("Verona", "VR", "Veneto", 45.4384, 10.9916),
            ("Vicenza", "VI", "Veneto", 45.5455, 11.5354),
        ]

        # Crea o aggiorna le città
        citta_create = 0
        citta_aggiornate = 0

        for nome, sigla, regione, lat, lon in province:
            citta, created = Citta.objects.update_or_create(
                nome=nome,
                defaults={
                    'provincia': sigla,
                    'regione': regione,
                    'latitudine': lat,
                    'longitudine': lon
                }
            )
            if created:
                citta_create += 1
            else:
                citta_aggiornate += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {citta_create} città create, {citta_aggiornate} aggiornate"
        ))

        # Calcola le distanze tra tutte le città
        self.stdout.write("\n📏 Calcolo distanze tra città...")

        tutte_citta = list(Citta.objects.all())
        distanze_create = 0

        for i, citta_a in enumerate(tutte_citta):
            for citta_b in tutte_citta[i+1:]:  # Solo coppie uniche
                distanza_km = self._calcola_distanza_haversine(
                    citta_a.latitudine, citta_a.longitudine,
                    citta_b.latitudine, citta_b.longitudine
                )

                # Crea la distanza (in una sola direzione, il metodo get_distanza cerca in entrambe)
                DistanzaCitta.objects.update_or_create(
                    citta_a=citta_a,
                    citta_b=citta_b,
                    defaults={'distanza_km': int(distanza_km)}
                )
                distanze_create += 1

            # Progress update ogni 10 città
            if (i + 1) % 10 == 0:
                self.stdout.write(f"  Processate {i+1}/{len(tutte_citta)} città...")

        self.stdout.write(self.style.SUCCESS(
            f"✅ {distanze_create} distanze calcolate"
        ))

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 Completato! {len(tutte_citta)} province italiane disponibili"
        ))

    def _calcola_distanza_haversine(self, lat1, lon1, lat2, lon2):
        """Calcola distanza in km tra due punti usando la formula di Haversine"""
        R = 6371  # Raggio della Terra in km

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c
