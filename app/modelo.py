"""
Modelo de IA da disciplina - classificador local de sentimento.

Classificador de sentimento (positivo/negativo) em portugues.
Treina localmente na primeira execucao e salva em disco (modelo.joblib).
Nao baixa nada da internet: funciona 100% offline no laboratorio.

Voce NAO precisa entender machine learning para usar isto.
So precisa saber: carregar_modelo() devolve um objeto com .prever(texto).
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

CAMINHO = os.path.join(os.path.dirname(__file__), "modelo.joblib")
VERSAO_MODELO = 3

# Mini base de treino embutida (suficiente para a disciplina).
TREINO = [
    ("o atendimento foi excelente e muito rapido", 1),
    ("adorei o produto, recomendo demais", 1),
    ("entrega pontual e embalagem perfeita", 1),
    ("otima qualidade pelo preco cobrado", 1),
    ("funcionou exatamente como prometido", 1),
    ("equipe super atenciosa, resolveram tudo", 1),
    ("melhor compra que fiz esse ano", 1),
    ("chegou antes do prazo, muito bom", 1),
    ("produto maravilhoso, superou expectativas", 1),
    ("simples de usar e muito eficiente", 1),
    ("pessimo atendimento, ninguem resolve nada", 0),
    ("produto quebrou no primeiro dia de uso", 0),
    ("entrega atrasou muito e ninguem avisou", 0),
    ("caro demais pelo que entrega", 0),
    ("nao funcionou como anunciado, decepcionante", 0),
    ("horrivel, quero meu dinheiro de volta", 0),
    ("suporte nunca responde, abandonado", 0),
    ("veio faltando peca e a embalagem rasgada", 0),
    ("qualidade muito ruim, nao recomendo", 0),
    ("perda de tempo e de dinheiro", 0),
    # Exemplos adicionais positivos (25).
    ("o atendimento foi muito atencioso", 1),
    ("a equipe resolveu tudo rapidamente", 1),
    ("fiquei muito satisfeito com a compra", 1),
    ("o produto tem qualidade excelente", 1),
    ("a entrega chegou antes do prazo", 1),
    ("o preco foi justo pela qualidade", 1),
    ("o suporte foi eficiente e educado", 1),
    ("tive uma experiencia muito agradavel", 1),
    ("recomendo muito este servico", 1),
    ("meu pedido chegou completo", 1),
    ("a embalagem protegeu muito bem o produto", 1),
    ("o sistema e facil de usar", 1),
    ("recebi uma resposta muito rapida", 1),
    ("resolveram meu problema no mesmo dia", 1),
    ("o aplicativo e intuitivo e pratico", 1),
    ("o material e resistente e bem feito", 1),
    ("o prazo combinado foi cumprido", 1),
    ("o funcionario foi educado e prestativo", 1),
    ("o servico foi impecavel", 1),
    ("voltaria a comprar sem duvida", 1),
    ("o resultado superou minhas expectativas", 1),
    ("minha satisfacao com o produto e total", 1),
    ("tudo esta funcionando perfeitamente", 1),
    ("o atendimento merece nota dez", 1),
    ("a compra valeu muito a pena", 1),
    # Casos curtos e variações comuns de avaliação positiva.
    ("bom", 1),
    ("muito bom", 1),
    ("foi bom", 1),
    ("o atendimento foi bom", 1),
    ("o atendimento foi otimo", 1),
    ("otimo atendimento", 1),
    ("produto bom", 1),
    ("gostei do atendimento", 1),
    ("servico bom", 1),
    ("experiencia positiva", 1),
    # Exemplos adicionais negativos (25).
    ("o atendimento foi ruim", 0),
    ("o atendimento foi pessimo", 0),
    ("fui mal atendido pela equipe", 0),
    ("o suporte ignorou minha mensagem", 0),
    ("a entrega chegou muito atrasada", 0),
    ("o produto veio com defeito", 0),
    ("a embalagem chegou danificada", 0),
    ("caro demais e com baixa qualidade", 0),
    ("nao recomendo este produto", 0),
    ("meu problema nao foi resolvido", 0),
    ("a resposta demorou varios dias", 0),
    ("o pedido chegou incompleto", 0),
    ("tive uma experiencia frustrante", 0),
    ("o aplicativo travou varias vezes", 0),
    ("o prazo prometido nao foi cumprido", 0),
    ("o funcionario foi grosseiro", 0),
    ("houve uma cobranca indevida", 0),
    ("o produto recebido era diferente do anunciado", 0),
    ("perdi meu tempo e meu dinheiro", 0),
    ("o servico foi decepcionante", 0),
    ("nunca mais vou comprar aqui", 0),
    ("a espera pelo atendimento foi longa", 0),
    ("as instrucoes eram confusas", 0),
    ("o produto veio quebrado", 0),
    ("a qualidade foi horrivel", 0),
]


class ModeloSentimento:
    """Envolve o pipeline treinado. Use apenas o metodo prever()."""

    def __init__(self, pipeline):
        self._pipeline = pipeline

    def prever(self, texto: str) -> dict:
        """Recebe um texto e devolve o rotulo e a confianca."""
        proba = self._pipeline.predict_proba([texto])[0]
        idx = int(proba.argmax())
        return {
            "texto": texto,
            "sentimento": "positivo" if idx == 1 else "negativo",
            "confianca": round(float(proba[idx]), 4),
        }


def _treinar():
    textos = [t for t, _ in TREINO]
    rotulos = [r for _, r in TREINO]
    pipe = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            strip_accents="unicode",
        ),
        LogisticRegression(max_iter=1000),
    )
    pipe.fit(textos, rotulos)
    joblib.dump({"versao": VERSAO_MODELO, "pipeline": pipe}, CAMINHO)
    return pipe


def carregar_modelo() -> ModeloSentimento:
    """Carrega o modelo do disco; treina na primeira vez. CHAME UMA VEZ SO."""
    if os.path.exists(CAMINHO):
        salvo = joblib.load(CAMINHO)
        if isinstance(salvo, dict) and salvo.get("versao") == VERSAO_MODELO:
            pipe = salvo["pipeline"]
        else:
            pipe = _treinar()
    else:
        pipe = _treinar()
    return ModeloSentimento(pipe)


if __name__ == "__main__":
    m = carregar_modelo()
    for frase in ["gostei muito do servico", "foi horrivel, nao volto mais"]:
        print(m.prever(frase))
