import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# Placeholders disponibles dans le gabarit de ligne (un par bien imprimé).
ASSET_PLACEHOLDERS = {
    "BienId": lambda asset: asset.bien_id,
    "Designation": lambda asset: asset.bien_designation,
    "DateSortie": lambda asset: asset.bien_amort_date_sortie,
    "Statut": lambda asset: "Actif" if asset.is_active else "Exclu",
    "NumeroLocal": lambda asset: asset.local_numero,
    "Immeuble": lambda asset: asset.immeuble_libelle,
    "Niveau": lambda asset: asset.niveau_libelle,
    "Local": lambda asset: asset.local_libelle,
}

# Placeholders disponibles dans le gabarit de nom de fichier, en plus
# des placeholders de ligne (ASSET_PLACEHOLDERS) : un lot n'a pas
# d'en-tête, seul le nom de fichier a besoin d'identifier le lot.
JOB_PLACEHOLDERS = {
    "JobId": lambda job_id: job_id,
}

DEFAULT_LINE_TEMPLATE = (
    "PRINT|bien_id={{BienId}}|designation={{Designation}}"
)

# Nom de fichier sans extension (".cmd" est toujours ajouté à la
# génération) ; accepte à la fois les placeholders d'en-tête et de
# ligne puisqu'un fichier combine généralement un identifiant de lot
# et un identifiant de bien.
DEFAULT_FILENAME_TEMPLATE = "print_job_{{JobId}}_{{BienId}}"


class DuplicateFilenameError(Exception):
    """
    Le gabarit de nom de fichier ne produit pas un nom distinct par
    bien du lot (ex. gabarit sans {{BienId}}) : générer écraserait
    silencieusement des fichiers déjà écrits pour ce même lot.
    """

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(
            f"Nom de fichier en doublon dans le lot : {filename}"
        )


class CommandGenerator:

    def __init__(
        self,
        output_dir=None
    ):

        self.output_dir = (
            Path(output_dir)
            if output_dir
            else BASE_DIR / "generated"
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def sanitize_value(
        self,
        value
    ) -> str:

        if value is None:
            return ""

        return (
            str(value)
            .replace("\r", " ")
            .replace("\n", " ")
            .replace("|", "-")
            .strip()
        )

    def render_template(
        self,
        template: str,
        placeholder_map: dict,
        context
    ) -> str:
        """
        Remplace chaque {{Placeholder}} du gabarit par la valeur
        correspondante (sanitisée). Un placeholder inconnu est laissé
        tel quel dans le résultat, pour rester visible plutôt que de
        disparaître silencieusement (aide à repérer une faute de frappe
        dans le gabarit).
        """

        def replace(match: re.Match) -> str:

            name = match.group(1)

            if name not in placeholder_map:
                return match.group(0)

            return self.sanitize_value(
                placeholder_map[name](context)
            )

        return PLACEHOLDER_PATTERN.sub(replace, template)

    def sanitize_filename(
        self,
        value
    ) -> str:
        """
        Comme sanitize_value, en interdisant en plus les caractères
        invalides dans un nom de fichier (le nom de fichier généré
        sert de nom de fichier, un caractère comme "/" casserait
        sinon le chemin).
        """

        text = re.sub(
            r'[\\/:*?"<>|]',
            "_",
            self.sanitize_value(value)
        )

        return text or "bien"

    def render_filename_template(
        self,
        template: str,
        job_id,
        asset
    ) -> str:
        """
        Comme render_template, mais accepte à la fois les placeholders
        d'en-tête ({{JobId}}) et de ligne ({{BienId}}, ...) puisqu'un
        nom de fichier combine généralement les deux. Le résultat est
        sanitisé pour être un nom de fichier valide (voir
        sanitize_filename).
        """

        def replace(match: re.Match) -> str:

            name = match.group(1)

            if name in JOB_PLACEHOLDERS:
                return self.sanitize_value(
                    JOB_PLACEHOLDERS[name](job_id)
                )

            if name in ASSET_PLACEHOLDERS:
                return self.sanitize_value(
                    ASSET_PLACEHOLDERS[name](asset)
                )

            return match.group(0)

        rendered = PLACEHOLDER_PATTERN.sub(replace, template)

        return self.sanitize_filename(rendered)

    def generate(
        self,
        job_id: int,
        assets: list,
        line_template: str = None,
        filename_template: str = None
    ) -> list:
        """
        Génère un fichier .cmd par bien du lot (un bien = une étiquette
        = un fichier, sans en-tête de lot), déposés directement dans
        output_dir (pas de sous-dossier), nommés d'après
        filename_template (§ render_filename_template, suffixé de
        ".cmd"). Retourne la liste triée des noms de fichiers écrits.
        """

        line_template = line_template or DEFAULT_LINE_TEMPLATE
        filename_template = filename_template or DEFAULT_FILENAME_TEMPLATE

        files = []
        seen_filenames = set()

        for asset in assets:

            line = self.render_template(
                line_template,
                ASSET_PLACEHOLDERS,
                asset
            )

            asset_filename = (
                f"{self.render_filename_template(filename_template, job_id, asset)}"
                ".cmd"
            )

            if asset_filename in seen_filenames:
                raise DuplicateFilenameError(asset_filename)

            seen_filenames.add(asset_filename)
            files.append((asset_filename, line))

        for asset_filename, content in files:

            # Le logiciel d'impression (Windows) exige des retours à la
            # ligne CRLF ("\r\n") et n'accepte pas un fichier en LF
            # seul ("\n") : plutôt que de compter sur la traduction
            # implicite de Python selon l'OS (peu fiable en pratique,
            # ex. un gabarit déjà en CRLF y échapperait sinon), on
            # normalise explicitement ici et on écrit avec newline=""
            # pour empêcher toute retraduction ultérieure.
            normalized = content.replace("\r\n", "\n").replace("\n", "\r\n")

            # Cas réel remonté par un utilisateur : un gabarit enregistré
            # sans retour à la ligne final (ex. dernière ligne du
            # textarea tronquée par erreur en le modifiant) produit un
            # fichier que le logiciel d'impression ignore silencieusement
            # sans erreur visible. On garantit donc toujours une fin de
            # ligne CRLF en fin de fichier, quel que soit le gabarit.
            if normalized and not normalized.endswith("\r\n"):
                normalized += "\r\n"

            (self.output_dir / asset_filename).write_text(
                normalized,
                encoding="utf-8",
                newline=""
            )

        return sorted(filename for filename, _ in files)
