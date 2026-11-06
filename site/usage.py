"""The usage section: an example Claude Code session, rendered like the terminal UI.

The session skeleton (tool calls and their outputs) is shared by every language; only what the user types,
what the agent says and its thinking are translated. Numbers are illustrative but consistent:
1,000 subs (800 D1 + 200 D2, 180 s), 962 kept by Frame Analysis, 4 more rejected by the user = 958
(768 D1 = 38.4 h, 190 D2 = 9.5 h).
"""

NB = "python3 ~/.claude/skills/nebulis/scripts/nebulis.py"

# (kind, payload). Kinds: user, think, skill, tool, say, note. Strings in {braces} are translated keys.
SESSION = [
    ("user", "{u1}"),
    ("skill", ("astro-processing", ["Successfully loaded skill"])),
    ("think", "{t1}"),
    ("tool", (f"Bash({NB} sessions Sh2-105)", [
        "2026-09-05  filters D1   exposures 180   subs 120",
        "2026-09-06  filters D1   exposures 180   subs 120",
        "… +7 lines (ctrl+o to expand)"])),
    ("say", "{a1}"),
    ("user", "{u2}"),
    ("tool", (f"Bash({NB} analysis Sh2-105 2026-09-08 --bad-only)", [
        "Sh2-105 2026-09-08 · measured 120/120 · kept 120/120",
        "grades: fair 4, good 116 · flags: soft 4",
        "typical frame: stars 812 · FWHM 2.6 px · elongation 1.08",
        "… +4 lines (ctrl+o to expand)"])),
    ("say", "{a2}"),
    ("user", "{u3}"),
    ("tool", (f"Bash({NB} review --reject Sh2-105/2026-09-08/Light_Sh2-105_180.0s_D1_0041.fit …)", [
        "4 frame(s) set to reject"])),
    ("tool", (f"Bash({NB} plan Sh2-105 --all)", [
        "Sh2-105 · nights 2026-09-05 … 2026-09-27",
        "lights 958 kept, 42 not kept · errors 0 · warnings 1",
        "  ! warning: flat_other_night {\"bundle\": \"Flat_D2_0.42s\", \"days\": 3}",
        "… +38 lines (ctrl+o to expand)"])),
    ("think", "{t2}"),
    ("say", "{a3}"),
    ("user", "{u4}"),
    ("tool", (f"Bash({NB} fetch Sh2-105 --all --dest ~/Astro/Processing/Sh2-105/data --allow-warnings)", [
        "unpacked to ~/Astro/Processing/Sh2-105/data/Sh2-105_9-nights_wbpp",
        "lights 958 (plan 958) · layout wbpp"])),
    ("tool", ("pixinsight - run_wbpp (MCP)(input_dirs: [\"…/data/Sh2-105_9-nights_wbpp\"], output_dir: \"wbpp\", "
              "keywords: [{name: \"NIGHT\", mode: \"pre\"}], rejection: \"Auto\", local_normalization: true)", [
        "WBPP started headless · run id 20261106-153204"])),
    ("tool", ("pixinsight - wbpp_status (MCP)(run_id: \"20261106-153204\")", [
        "finished · exit code 0 · 41m 12s",
        "master/masterLight_FILTER-D1_EXPTIME-180.xisf",
        "master/masterLight_FILTER-D2_EXPTIME-180.xisf"])),
    ("say", "{a4}"),
    ("note", "{n1}"),
    ("tool", ("pixinsight - get_image_stats (MCP)(view_id: \"HOO_s3\")", [
        "median 0.251 · clampFractions at 1: R 0.0014, G 0.0009, B 0.0011"])),
    ("say", "{a5}"),
    ("user", "{u5}"),
    ("tool", ("pixinsight - export_image (MCP)(view_id: \"Sh2_105_Foraxx\", file_path: \"final/Sh2-105_Foraxx_2026-11-06.xisf\")", [
        "Wrote output/final/Sh2-105_Foraxx_2026-11-06.xisf (32-bit)"])),
    ("say", "{a6}"),
    ("user", "{u6}"),
    ("tool", (f"Bash({NB} push Sh2-105 --bundle output/push --name Sh2-105_2026-11-06_processing.zip)", [
        "stored Sh2-105_2026-11-06_processing.zip (41.3 MB) with Sh2-105"])),
    ("say", "{a7}"),
]

USAGE = {
    "en": {
        "nav": "Use", "title": "Using it",
        "lead": "Open your coding agent in a terminal and ask in plain words. The agent loads the skill, then walks you through the stages, calling Nebulis and PixInsight as it goes. An example session:",
        "caption": "Example session, shortened. Numbers are illustrative.",
        "u1": "Process Sh2-105 with astro-processing.",
        "t1": "The user wants a full processing run. Stage 0: check Nebulis, then list the nights and pick the path from the filters.",
        "a1": "Nebulis 2.2.0 connected. Sh2-105 has 9 nights: 7 with D1, 2 with D2, 180 s, gain 200. That is the narrowband path. Process all 9 nights?",
        "u2": "yes",
        "a2": "Sub review: 962 of 1,000 subs kept; the night of 09-12 lost 31 subs to clouds. On 09-08, 4 subs are graded fair: soft stars, FWHM 3.4 px against 2.6. Keep or reject them?",
        "u3": "reject the 4 soft ones",
        "t2": "One warning: D2 flats 3 days from the D2 nights. Allowed by rule R1 only if the rotator angle did not change. Ask, do not assume.",
        "a3": "Done in Nebulis. Calibration plan: 0 errors, 1 warning. The D2 flats are 3 days from the D2 nights, same filter. Was the rotator angle unchanged during the campaign?",
        "u4": "unchanged, accept",
        "a4": "WBPP finished: D1 master 38.4 h, D2 master 9.5 h, both 3-channel. Next, crop, BXT correction and plate solve: astrometry 0.08 px, pass. Then the gradient: proposal and preview below.",
        "n1": "gradient · channels · deconvolution · noise reduction · one approval each",
        "a5": "Three stretch candidates side by side. s3 clips 0.14 % of pixels to white, above the 0.1 % gate: rejected. s1 or s2?",
        "u5": "s2, and show me HOO against the Foraxx palette",
        "a6": "Foraxx kept. Exported final/Sh2-105_Foraxx_2026-11-06 as .xisf, .tif and .jpg, and wrote PROCESSING.md. Store them with Sh2-105 in Nebulis?",
        "u6": "yes",
        "a7": "Stored in Nebulis under Project archives. The final image is open in PixInsight; every other view of this session is closed.",
        "tips_title": "Good to know",
        "tips": [
            ("Pick up later", "Say “continue Sh2-105”: the agent reads its session file and resumes at the first stage not done."),
            ("Let a stage run alone", "Say “run stacking without asking”: that stage no longer waits, for this session only."),
            ("Nebulis on its own", "“Which subs were bad last night on NGC 6888?” or “fetch Sh2-112 for stacking” use only the nebulis skill."),
            ("Change a value", "Answer a proposal with another value (“denoise 0.4”); the agent keeps it for the rest of the session and logs it."),
        ],
    },
    "fr": {
        "nav": "Utiliser", "title": "Utilisation",
        "lead": "Ouvrez votre agent de code dans un terminal et demandez en langage courant. L'agent charge le skill, puis vous fait passer les étapes une à une en appelant Nebulis et PixInsight. Une session type :",
        "caption": "Session d'exemple, raccourcie. Les chiffres sont illustratifs.",
        "u1": "Traite Sh2-105 avec astro-processing.",
        "t1": "L'utilisateur veut un traitement complet. Étape 0 : vérifier Nebulis, puis lister les nuits et choisir le chemin d'après les filtres.",
        "a1": "Nebulis 2.2.0 connecté. Sh2-105 compte 9 nuits : 7 en D1, 2 en D2, 180 s, gain 200. C'est le chemin narrowband. Je traite les 9 nuits ?",
        "u2": "oui",
        "a2": "Revue des subs : 962 sur 1 000 gardés ; la nuit du 12/09 a perdu 31 subs à cause des nuages. Le 08/09, 4 subs sont notés moyens : étoiles molles, FWHM 3,4 px contre 2,6. Je les garde ou je les rejette ?",
        "u3": "rejette les 4 subs mous",
        "t2": "Un avertissement : flats D2 à 3 jours des nuits D2. Admis par la règle R1 seulement si l'angle du rotateur n'a pas changé. Demander, ne rien supposer.",
        "a3": "C'est fait dans Nebulis. Plan de calibration : 0 erreur, 1 avertissement. Les flats D2 datent de 3 jours après les nuits D2, même filtre. L'angle du rotateur est-il resté le même pendant la campagne ?",
        "u4": "il n'a pas bougé, accepte",
        "a4": "WBPP terminé : master D1 38,4 h, master D2 9,5 h, tous deux en 3 canaux. Ensuite recadrage, correction BXT et résolution astrométrique : 0,08 px, validé. Puis le gradient : proposition et aperçu ci-dessous.",
        "n1": "gradient · canaux · déconvolution · débruitage · une validation à chaque fois",
        "a5": "Trois stretchs candidats côte à côte. s3 sature 0,14 % des pixels au blanc, au-delà du seuil de 0,1 % : rejeté. s1 ou s2 ?",
        "u5": "s2, et montre-moi HOO face à la palette Foraxx",
        "a6": "Foraxx retenue. Exporté final/Sh2-105_Foraxx_2026-11-06 en .xisf, .tif et .jpg, et rédigé PROCESSING.md. Je les range avec Sh2-105 dans Nebulis ?",
        "u6": "oui",
        "a7": "Rangé dans Nebulis, sous Project archives. L'image finale reste ouverte dans PixInsight ; toutes les autres vues de la session sont fermées.",
        "tips_title": "Bon à savoir",
        "tips": [
            ("Reprendre plus tard", "Dites « continue Sh2-105 » : l'agent relit son fichier de session et reprend à la première étape non terminée."),
            ("Laisser une étape tourner seule", "Dites « lance l'empilement sans me demander » : cette étape n'attend plus, pour cette session seulement."),
            ("Nebulis tout seul", "« Quels subs étaient mauvais hier soir sur NGC 6888 ? » ou « récupère Sh2-112 pour l'empiler » n'utilisent que le skill nebulis."),
            ("Changer une valeur", "Répondez à une proposition avec une autre valeur (« denoise 0,4 ») ; l'agent la garde pour la suite de la session et la consigne."),
        ],
    },
    "es": {
        "nav": "Uso", "title": "Cómo se usa",
        "lead": "Abre tu agente de código en un terminal y pide lo que quieras con tus palabras. El agente carga el skill y te guía por las etapas, llamando a Nebulis y a PixInsight sobre la marcha. Una sesión de ejemplo:",
        "caption": "Sesión de ejemplo, abreviada. Las cifras son ilustrativas.",
        "u1": "Procesa Sh2-105 con astro-processing.",
        "t1": "El usuario quiere un procesado completo. Etapa 0: comprobar Nebulis, luego listar las noches y elegir la ruta según los filtros.",
        "a1": "Nebulis 2.2.0 conectado. Sh2-105 tiene 9 noches: 7 con D1, 2 con D2, 180 s, ganancia 200. Es la ruta de banda estrecha. ¿Proceso las 9 noches?",
        "u2": "sí",
        "a2": "Revisión de tomas: se conservan 962 de 1.000; la noche del 12/09 perdió 31 tomas por nubes. El 08/09, 4 tomas tienen nota media: estrellas blandas, FWHM 3,4 px frente a 2,6. ¿Las conservo o las descarto?",
        "u3": "descarta las 4 blandas",
        "t2": "Un aviso: flats D2 a 3 días de las noches D2. La regla R1 lo admite solo si el ángulo del rotador no cambió. Preguntar, no suponer.",
        "a3": "Hecho en Nebulis. Plan de calibración: 0 errores, 1 aviso. Los flats D2 son de 3 días después de las noches D2, mismo filtro. ¿El ángulo del rotador se mantuvo durante la campaña?",
        "u4": "no cambió, acepta",
        "a4": "WBPP terminado: máster D1 38,4 h, máster D2 9,5 h, ambos de 3 canales. Después, recorte, corrección BXT y resolución astrométrica: 0,08 px, correcto. Luego el gradiente: propuesta y vista previa abajo.",
        "n1": "gradiente · canales · deconvolución · reducción de ruido · una aprobación cada vez",
        "a5": "Tres estirados candidatos lado a lado. s3 satura el 0,14 % de los píxeles en blanco, por encima del umbral del 0,1 %: descartado. ¿s1 o s2?",
        "u5": "s2, y enséñame HOO frente a la paleta Foraxx",
        "a6": "Me quedo con Foraxx. Exportado final/Sh2-105_Foraxx_2026-11-06 en .xisf, .tif y .jpg, y redactado PROCESSING.md. ¿Los guardo con Sh2-105 en Nebulis?",
        "u6": "sí",
        "a7": "Guardado en Nebulis, en Project archives. La imagen final sigue abierta en PixInsight; el resto de vistas de la sesión están cerradas.",
        "tips_title": "Conviene saber",
        "tips": [
            ("Retomar más tarde", "Di «continúa Sh2-105»: el agente relee su archivo de sesión y sigue en la primera etapa pendiente."),
            ("Dejar que una etapa vaya sola", "Di «apila sin preguntarme»: esa etapa ya no espera, solo en esta sesión."),
            ("Nebulis por separado", "«¿Qué tomas salieron mal anoche en NGC 6888?» o «descarga Sh2-112 para apilar» solo usan el skill nebulis."),
            ("Cambiar un valor", "Responde a una propuesta con otro valor («denoise 0,4»); el agente lo mantiene el resto de la sesión y lo registra."),
        ],
    },
    "it": {
        "nav": "Uso", "title": "Come si usa",
        "lead": "Apri il tuo agente di coding in un terminale e chiedi a parole tue. L'agente carica la skill e ti accompagna fase per fase, chiamando Nebulis e PixInsight strada facendo. Una sessione di esempio:",
        "caption": "Sessione di esempio, abbreviata. I numeri sono illustrativi.",
        "u1": "Elabora Sh2-105 con astro-processing.",
        "t1": "L'utente vuole un'elaborazione completa. Fase 0: controllare Nebulis, poi elencare le notti e scegliere il percorso in base ai filtri.",
        "a1": "Nebulis 2.2.0 collegato. Sh2-105 ha 9 notti: 7 con D1, 2 con D2, 180 s, gain 200. È il percorso a banda stretta. Elaboro tutte e 9 le notti?",
        "u2": "sì",
        "a2": "Revisione dei sub: 962 su 1.000 tenuti; la notte del 12/09 ha perso 31 sub per le nuvole. L'08/09, 4 sub hanno voto medio: stelle morbide, FWHM 3,4 px contro 2,6. Li tengo o li scarto?",
        "u3": "scarta i 4 morbidi",
        "t2": "Un avviso: flat D2 a 3 giorni dalle notti D2. Ammesso dalla regola R1 solo se l'angolo del rotatore non è cambiato. Chiedere, non supporre.",
        "a3": "Fatto in Nebulis. Piano di calibrazione: 0 errori, 1 avviso. I flat D2 sono di 3 giorni dopo le notti D2, stesso filtro. L'angolo del rotatore è rimasto invariato durante la campagna?",
        "u4": "invariato, accetta",
        "a4": "WBPP finito: master D1 38,4 h, master D2 9,5 h, entrambi a 3 canali. Poi ritaglio, correzione BXT e risoluzione astrometrica: 0,08 px, superato. Quindi il gradiente: proposta e anteprima qui sotto.",
        "n1": "gradiente · canali · deconvoluzione · riduzione del rumore · un'approvazione ciascuno",
        "a5": "Tre stretch candidati affiancati. s3 satura di bianco lo 0,14 % dei pixel, oltre la soglia dello 0,1 %: scartato. s1 o s2?",
        "u5": "s2, e mostrami HOO a confronto con la palette Foraxx",
        "a6": "Tengo Foraxx. Esportato final/Sh2-105_Foraxx_2026-11-06 in .xisf, .tif e .jpg, e scritto PROCESSING.md. Li salvo con Sh2-105 in Nebulis?",
        "u6": "sì",
        "a7": "Salvato in Nebulis, in Project archives. L'immagine finale resta aperta in PixInsight; tutte le altre viste della sessione sono chiuse.",
        "tips_title": "Da sapere",
        "tips": [
            ("Riprendere più tardi", "Di' «continua Sh2-105»: l'agente rilegge il suo file di sessione e riparte dalla prima fase non conclusa."),
            ("Lasciare andare da sola una fase", "Di' «integra senza chiedermi»: quella fase non aspetta più, solo per questa sessione."),
            ("Nebulis da solo", "«Quali sub erano cattivi ieri sera su NGC 6888?» o «scarica Sh2-112 per integrarlo» usano solo la skill nebulis."),
            ("Cambiare un valore", "Rispondi a una proposta con un altro valore («denoise 0,4»); l'agente lo tiene per il resto della sessione e lo registra."),
        ],
    },
}


def resolve(text, strings):
    if text.startswith("{") and text.endswith("}"):
        return strings[text[1:-1]]
    return text
