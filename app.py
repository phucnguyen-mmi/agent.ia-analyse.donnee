from flask import Flask, request, render_template
import anthropic
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Important : mode sans interface graphique
import matplotlib.pyplot as plt
import io
import base64
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    analyse = None
    graphique = None

    if request.method == "POST":
        fichier = request.files["csv"]
        df = pd.read_csv(fichier, encoding='utf-8', on_bad_lines='skip', engine='python')
        df = df.head(200)
        

        # ── Analyse par Claude ──────────────────────────────────────
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        prompt = f"""
        Tu es un expert en analyse de données marketing.
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

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        graphique = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()

    return render_template("index.html", analyse=analyse, graphique=graphique)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
