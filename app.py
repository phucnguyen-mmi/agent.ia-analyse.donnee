from flask import Flask, request, render_template, session, send_file, redirect, url_for
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import anthropic
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Important : mode sans interface graphique
import matplotlib.pyplot as plt
import io
import base64
import os
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///analyses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class AnalyseRecord(db.Model):
    __tablename__ = 'analyse'
    id = db.Column(db.Integer, primary_key=True)
    nom_fichier = db.Column(db.String(255))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    texte = db.Column(db.Text)
    graphique = db.Column(db.Text)
    csv_contenu = db.Column(db.Text)


with app.app_context():
    db.create_all()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password.strip() == os.environ.get("APP_PASSWORD", "").strip():
            session['authenticated'] = True
            return redirect(url_for('index'))
        error = "Mot de passe incorrect."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    analyse = None
    graphique = None

    if request.method == "POST":
        fichier = request.files["csv"]
        nom_fichier = fichier.filename
        df = pd.read_csv(fichier, encoding='utf-8', on_bad_lines='skip', engine='python')
        df = df.head(200)

        # ── Analyse par Claude ──────────────────────────────────────
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        prompt = f"""
        Tu es un expert en analyse de données marketing.
        Réponds en texte brut uniquement, sans markdown, sans symboles # ni *.
        Voici les données :

        {df.to_string()}

        Donne-moi :
        1. Les tendances principales
        2. Les points forts et points faibles
        3. 3 recommandations concrètes
        """

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        analyse = message.content[0].text

        # ── Graphique ───────────────────────────────────────────────
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        colonnes_numeriques = df.select_dtypes(include="number").columns.tolist()

        if len(colonnes_numeriques) >= 1:
            col_principale = colonnes_numeriques[0]
            top10 = df.nlargest(10, col_principale)

            if "Title" in df.columns:
                label_col = "Title"
            elif "title" in df.columns:
                label_col = "title"
            else:
                label_col = df.select_dtypes(include="object").columns[0]

            axes[0].barh(top10[label_col].astype(str), top10[col_principale], color="steelblue")
            axes[0].set_title(f"Top 10 par {col_principale}")
            axes[0].set_xlabel(col_principale)
            axes[0].invert_yaxis()

            if len(colonnes_numeriques) >= 2:
                col2 = colonnes_numeriques[1]
                axes[1].hist(df[col2].dropna(), bins=20, color="coral", edgecolor="white")
                axes[1].set_title(f"Distribution de {col2}")
                axes[1].set_xlabel(col2)
                axes[1].set_ylabel("Nombre de films")
            else:
                axes[1].axis("off")

        plt.tight_layout()

        # Sauvegarde dans un fichier temp pour la génération PDF
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(tmp.name, format="png", dpi=100)
        tmp.close()

        # Encodage base64 pour l'affichage HTML et la base de données
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        graphique = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

        # Stockage en session pour le téléchargement PDF
        session['analyse'] = analyse
        session['graphique_path'] = tmp.name

        # Sauvegarde en base de données
        record = AnalyseRecord(
            nom_fichier=nom_fichier,
            texte=analyse,
            graphique=graphique,
            csv_contenu=df.to_csv(index=False),
        )
        db.session.add(record)
        db.session.commit()

    return render_template("index.html", analyse=analyse, graphique=graphique)


@app.route("/telecharger-pdf")
@login_required
def telecharger_pdf():
    analyse = session.get('analyse')
    graphique_path = session.get('graphique_path')

    if not analyse:
        return "Aucune analyse disponible. Veuillez d'abord analyser un fichier CSV.", 400

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        'body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )

    elements = []
    elements.append(Paragraph("Rapport d'analyse marketing", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Analyse par Claude IA", styles['Heading2']))
    elements.append(Spacer(1, 0.3 * cm))

    for line in analyse.split('\n'):
        line = line.strip()
        if line:
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            elements.append(Paragraph(line, body_style))
        else:
            elements.append(Spacer(1, 0.2 * cm))

    if graphique_path and os.path.exists(graphique_path):
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Graphiques", styles['Heading2']))
        elements.append(Spacer(1, 0.3 * cm))
        img_width = 17 * cm
        elements.append(RLImage(graphique_path, width=img_width, height=img_width * 5 / 14))

    doc.build(elements)

    if graphique_path and os.path.exists(graphique_path):
        try:
            os.unlink(graphique_path)
            session.pop('graphique_path', None)
        except OSError:
            pass

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="rapport_marketing.pdf",
        mimetype="application/pdf",
    )


@app.route("/historique")
@login_required
def historique():
    date_filtre = request.args.get('date', '')
    query = AnalyseRecord.query.order_by(AnalyseRecord.date.desc())
    if date_filtre:
        try:
            d = datetime.strptime(date_filtre, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AnalyseRecord.date) == d)
        except ValueError:
            pass
    analyses = query.all()
    return render_template("historique.html", analyses=analyses, date_filtre=date_filtre)


@app.route("/historique/<int:id>")
@login_required
def voir_analyse(id):
    a = AnalyseRecord.query.get_or_404(id)
    return render_template("voir_analyse.html", analyse=a)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
