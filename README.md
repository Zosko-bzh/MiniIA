# MiniIA — chatbot local

Petit chatbot façon ChatGPT conçu pour fonctionner localement sur un PC avec peu de VRAM.

## Configuration cible

- RTX 3050 Laptop 4 Go VRAM
- 8 Go RAM minimum
- Windows
- Python 3.11 recommandé

## 1. Installer Python

Installe Python 3.11 et coche **Add Python to PATH**.

## 2. Installer les dépendances

Dans le dossier du projet :

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Si l'installation de llama-cpp-python échoue

Tu peux installer une version précompilée adaptée à ton environnement, ou utiliser une version CPU de llama-cpp-python. Le projet reste fonctionnel, mais l'inférence sera plus lente.

## 3. Ajouter le modèle

Le projet attend :

```text
models/model.gguf
```

Choisis un petit modèle conversationnel au format GGUF, idéalement autour de 3B à 4B paramètres et quantifié en Q4.

Renomme le fichier en :

```text
model.gguf
```

## 4. Lancer

Double-clique sur :

```text
start.bat
```

Puis ouvre :

http://127.0.0.1:5000

## Réglages pour la RTX 3050

Le code utilise :

- `n_gpu_layers=-1` : essaie de charger les couches sur le GPU
- contexte de 2048 tokens
- génération limitée à 512 tokens

Si la VRAM sature, baisse `n_ctx` à 1024 ou mets `n_gpu_layers=0` pour tester en CPU.

## Évolution prévue

Le projet peut ensuite recevoir :

- mémoire persistante
- conversations multiples
- import PDF/TXT
- RAG
- recherche web
- vision
- voix
- personnalisation du modèle
- interface plus avancée
