# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3
#     name: python3
# ---

# %% [markdown] id="7YQjiOqtVsWI"
# # LangGraph Introduction
#
# ## Contexte
#
# LangChain facilite la création d'applications basées sur les LLM. L'un des types d'applications que vous pouvez construire est un Agent. Il y a beaucoup d'enthousiasme autour de la création d'Agents, car ils peuvent automatiser une grande variété de tâches qui étaient auparavant impossibles.
#
# En pratique cependant, il est incroyablement difficile de construire des systèmes qui exécutent ces tâches de manière fiable. Par exemple, vous pourriez avoir besoin qu'un agent appelle toujours un outil spécifique en premier, ou utilise des prompts différents en fonction de son état.
#
# Pour résoudre ce problème, il y a [LangGraph](https://langchain-ai.github.io/langgraph/) : un framework pour construire des applications mono-agent et multi-agents. Séparé du package LangChain, la philosophie de conception centrale de LangGraph est d'aider les développeurs à ajouter plus de précision et de contrôle dans les flux de travail des agents, adaptés à la complexité des systèmes du monde réel.
#
# ## Modèles de chat
#
# Dans ce cours, nous utiliserons les [Chat Models](https://python.langchain.com/v0.2/docs/concepts/#chat-models), qui prennent en entrée une séquence de messages et renvoient en sortie des messages de chat. LangChain n'héberge pas de modèles de chat, nous comptons plutôt sur des intégrations tierces. [Ici](https://python.langchain.com/v0.2/docs/integrations/chat/) se trouve une liste des intégrations de modèles de chat tiers disponibles dans LangChain ! Par défaut, le cours utilisera [ChatOpenAI](https://python.langchain.com/v0.2/docs/integrations/chat/openai/), car il est à la fois populaire et performant. Comme indiqué, assurez-vous de disposer d'une clé `OPENAI_API_KEY`.
#
# Vérifions que votre `OPENAI_API_KEY` est bien défini et, si ce n'est pas le cas, vous serez invité à le saisir.

# %% id="lfbdKnT_TRwh"
# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langchain_community tavily-python

# %% id="lnGlBZXyX3P1"
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

# %% [markdown] id="Z5ZSd2ahedNs"
# [Voici](https://python.langchain.com/v0.2/docs/how_to/#chat-models) un guide pratique utile pour toutes les fonctionnalités possibles avec les modèles de chat, mais nous allons présenter ci-dessous quelques points essentiels.
#
# Par défaut, les notebooks utiliseront `gpt-4o`, car il offre un bon équilibre entre qualité, prix et rapidité [voir plus d'informations ici](https://help.openai.com/en/articles/7102672-how-can-i-access-gpt-4-gpt-4-turbo-gpt-4o-and-gpt-4o-mini), mais vous pouvez aussi opter pour les modèles de la série `gpt-3.5`, qui sont moins chers.
#
# Il existe [quelques paramètres standards](https://python.langchain.com/v0.2/docs/concepts/#chat-models) que nous pouvons configurer avec les modèles de chat. Deux des plus courants sont :
#
# * `model` : le nom du modèle
# * `temperature` : la température
#
# La `temperature` contrôle l'aléatoire ou la créativité des réponses du modèle : une température basse (proche de 0) donne des sorties plus déterministes et ciblées. C'est utile pour les tâches nécessitant de la précision ou des réponses factuelles. Une température élevée (proche de 1) est adaptée aux tâches créatives ou à la génération de réponses variées.

# %% id="LJsXSgmzX9lX"
from langchain_openai import ChatOpenAI
gpt4o_chat = ChatOpenAI(model="gpt-4o", temperature=0)

# %% [markdown] id="_IiJJbt_e94k"
# Les modèles de chat dans LangChain disposent d'un certain nombre de [méthodes par défaut](https://python.langchain.com/v0.2/docs/concepts/#runnable-interface). La plupart du temps, nous utiliserons :
#
# * `stream` : renvoyer le flux de réponse token par token
# * `invoke` : appeler la chaîne sur une entrée
#
# Comme mentionné, les modèles de chat prennent des [messages](https://python.langchain.com/v0.2/docs/concepts/#messages) en entrée. Les messages possèdent un rôle (qui décrit qui parle) et une propriété de contenu. Nous en reparlerons beaucoup plus en détail plus tard, mais pour l'instant, voyons simplement les bases.

# %% colab={"base_uri": "https://localhost:8080/"} id="nAhkK1ZoYfPp" outputId="d55e6419-4d54-45df-d974-75381397fe6e"
from langchain_core.messages import HumanMessage

# Create a message
msg = HumanMessage(content="Hello world", name="Lance")

# Message list
messages = [msg]

# Invoke the model with a list of messages
gpt4o_chat.invoke(messages)

# %% [markdown] id="I8TcAwIzfYoo"
# Nous obtenons une réponse de type `AIMessage`. Notez également que nous pouvons simplement invoquer un modèle de chat avec une chaîne de caractères. Lorsqu'une chaîne est transmise en entrée, elle est convertie en `HumanMessage` puis envoyée au modèle sous-jacent.

# %% [markdown] id="J4MfRsdQfwGp"
# ## Outils de recherche
#
# [Tavily](https://tavily.com/) s'agit d'un moteur de recherche optimisé pour les LLM et le RAG, conçu pour fournir des résultats de recherche efficaces, rapides et persistants. Comme indiqué, l'inscription est simple et Tavily propose une offre gratuite généreuse. Nous utiliserons Tavily par défaut mais, bien sûr, vous pouvez utiliser d'autres outils de recherche si vous souhaitez modifier le code vous-même.

# %% colab={"base_uri": "https://localhost:8080/"} id="dZjwiUmJe0ZK" outputId="c1a48833-18e0-4fc6-ace8-2271c748a089"
_set_env("TAVILY_API_KEY")

# %% id="BquM_iuOgc5d"
from langchain_community.tools.tavily_search import TavilySearchResults
tavily_search = TavilySearchResults(max_results=3)
search_docs = tavily_search.invoke("Qu'est-ce que LangGraph?")

# %% colab={"base_uri": "https://localhost:8080/"} id="QE-RWYk0givN" outputId="f0b21f9e-dddc-47db-b2f9-f5c8d02c24e2"
search_docs

# %% [markdown] id="kCBFPITchIsv"
# # Le graphe le plus simple
#
# Construisons un graphe simple avec 3 nœuds et une arête conditionnelle.
#
# ![Capture d’écran 2024-08-20 à 15.11.22.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dba5f465f6e9a2482ad935_simple-graph1.png)
#

# %% id="iXQTWEtVgt8t"
# %%capture --no-stderr
# %pip install --quiet -U langgraph

# %% [markdown] id="mtLvL3LEhYW_"
# ## État
#
# Tout d'abord, définissons l'[État](https://langchain-ai.github.io/langgraph/concepts/low_level/#state) du graphe.
#
# Le schéma de l'État sert de schéma d'entrée pour tous les Nœuds et Arêtes du graphe.
#
# Utilisons la classe `TypedDict` du module `typing` de Python comme schéma, qui fournit des annotations de type pour les clés.
#

# %% id="hYgnBFEnhh6k"
from typing_extensions import TypedDict

class State(TypedDict):
    graph_state: str


# %% [markdown] id="yO40jB8Jhjxv"
# ## Nœuds
#
# Les [Nœuds](https://langchain-ai.github.io/langgraph/concepts/low_level/#nodes) sont simplement des fonctions Python.
#
# Le premier argument positionnel est l'état, tel que défini ci-dessus.
#
# Comme l'état est un `TypedDict` avec le schéma défini précédemment, chaque nœud peut accéder à la clé `graph_state` via `state['graph_state']`.
#
# Chaque nœud retourne une nouvelle valeur pour la clé d'état `graph_state`.
#
# Par défaut, la nouvelle valeur renvoyée par chaque nœud [remplacera](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) la valeur précédente de l'état.
#

# %% id="gDNE7bORhP5M"
def node_1(state):
    print("---Node 1---")
    return {"graph_state": state['graph_state'] +" I am"}

def node_2(state):
    print("---Node 2---")
    return {"graph_state": state['graph_state'] +" happy!"}

def node_3(state):
    print("---Node 3---")
    return {"graph_state": state['graph_state'] +" sad!"}


# %% [markdown] id="BpC0XidHh_0A"
# ## Arêtes
#
# Les [Arêtes](https://langchain-ai.github.io/langgraph/concepts/low_level/#edges) connectent les nœuds.
#
# Les arêtes normales sont utilisées si vous voulez *toujours* aller, par exemple, de `node_1` vers `node_2`.
#
# Les [Arêtes conditionnelles](https://langchain-ai.github.io/langgraph/concepts/low_level/#conditional-edges) sont utilisées si vous voulez *éventuellement* diriger le flux entre différents nœuds.
#
# Les arêtes conditionnelles sont implémentées sous forme de fonctions qui renvoient le prochain nœud à visiter en fonction d'une logique donnée.
#

# %% id="20Xyt3q4h0yt"
import random
from typing import Literal

def decide_mood(state) -> Literal["node_2", "node_3"]:

    # Often, we will use state to decide on the next node to visit
    user_input = state['graph_state']

    # Here, let's just do a 50 / 50 split between nodes 2, 3
    if random.random() < 0.5:

        # 50% of the time, we return Node 2
        return "node_2"

    # 50% of the time, we return Node 3
    return "node_3"


# %% [markdown] id="g0CUCLLTijKF"
# Voici la traduction en français :
#
# ---
#
# ## Construction du graphe
#
# Nous allons maintenant construire le graphe à partir de nos [composants](https://langchain-ai.github.io/langgraph/concepts/low_level/) définis ci-dessus.
#
# La classe [StateGraph](https://langchain-ai.github.io/langgraph/concepts/low_level/#stategraph) est la classe de graphe que nous pouvons utiliser.
#
# Tout d'abord, nous initialisons un `StateGraph` avec la classe `State` que nous avons définie précédemment.
#
# Ensuite, nous ajoutons nos nœuds et nos arêtes.
#
# Nous utilisons le [`START` Node, un nœud spécial](https://langchain-ai.github.io/langgraph/concepts/low_level/#start-node) qui envoie l'entrée de l'utilisateur au graphe, pour indiquer où commence notre graphe.
#
# Le [`END` Node](https://langchain-ai.github.io/langgraph/concepts/low_level/#end-node) est un nœud spécial qui représente un nœud terminal.
#
# Enfin, nous [compilons notre graphe](https://langchain-ai.github.io/langgraph/concepts/low_level/#compiling-your-graph) afin d'effectuer quelques vérifications de base sur la structure du graphe.
#
# Nous pouvons visualiser le graphe sous forme de [diagramme Mermaid](https://github.com/mermaid-js/mermaid).

# %% colab={"base_uri": "https://localhost:8080/", "height": 350} id="chTpREZiia6P" outputId="a8d73dc2-f057-4248-bb8e-0a43abe56c19"
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
display(Image(graph.get_graph().draw_mermaid_png()))

# %% [markdown] id="TSN__5eSjaLN"
# ## Invocation du graphe
#
# Le graphe compilé implémente le protocole [runnable](https://python.langchain.com/docs/concepts/runnables/).
#
# Cela fournit une manière standard d'exécuter les composants LangChain.
#
# `invoke` est l'une des méthodes standards de cette interface.
#
# L'entrée est un dictionnaire `{"graph_state": "Hi, this is lance."}`, qui définit la valeur initiale de notre dictionnaire d'état du graphe.
#
# Lorsque `invoke` est appelé, le graphe commence son exécution à partir du nœud `START`.
#
# Il progresse ensuite à travers les nœuds définis (`node_1`, `node_2`, `node_3`) dans l'ordre.
#
# L'arête conditionnelle fera passer du nœud `1` au nœud `2` ou `3` en utilisant une règle de décision 50/50.
#
# Chaque fonction de nœud reçoit l'état courant et renvoie une nouvelle valeur, qui remplace l'état du graphe.
#
# L'exécution continue jusqu'à ce qu'elle atteigne le nœud `END`.
#

# %% colab={"base_uri": "https://localhost:8080/"} id="R5bdAreLinwt" outputId="d4e7b544-a2b4-4a40-a576-a4c0f799f167"
graph.invoke({"graph_state" : "Hi, this is Lance."})

# %% id="WI86lqLZdhf9"
from __future__ import annotations
import json
from typing import Literal, TypedDict

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt_template_mood = """
  Tu es un classificateur d’émotions binaire. Tu dois décider si un 'MESSAGE' exprime l'émotion "Happy" ou "Sad".
  Les règles de décision sont les suivantes :
  - HAPPY : joie, satisfaction, optimisme, gratitude, humour, soulagement.
  - SAD : tristesse, colère, peur, anxiété, déception, amertume, plainte.
  Choisis l’émotion DOMINANTE ressentie par l’énonciateur.
  Pas d’explications, pas de texte hors JSON, pas de guillemets autour des clés JSON, respecte exactement la casse de "Happy"/"Sad".

  Exemples :
  Input: "Je suis tellement content de la nouvelle !"
  Output: {{'mood': "Happy"}}

  Input: "Rien ne va aujourd’hui, j’en ai marre."
  Output: {{'mood': "Sad"}}

  Input: "C’était dur, mais je me sens enfin mieux."
  Output: {{'mood': "Happy"}}

  Input: "J’ai raté l’entretien et je me sens nul."
  Output: {{'mood': "Sad"}}

  FORMAT DE SORTIE UNIQUE ET STRICT :
  {{'mood': "Happy"}} ou {{'mood': "Sad"}}

  MESSAGE :
  {message}
""".strip()

model = ChatOpenAI(
    model="gpt-4o-mini",  # ou "gpt-4o" selon votre offre
    temperature=0,
    # azure_deployment="my-deployment-name"  # décommentez si vous êtes sur Azure
)

prompt = PromptTemplate.from_template(prompt_template_mood)

# --- 3) Validation stricte du JSON ---
class MoodDict(TypedDict):
    mood: Literal["Happy", "Sad"]

def _strict_json_validator(text: str) -> MoodDict:
    """
    Valide que `text` est exactement un objet JSON au format:
    {'mood': "Happy"} ou {'mood': "Sad"}
    On tolère guillemets simples ou doubles et espaces.
    """
    # Normaliser en JSON valide si l'IA met des quotes simples
    normalized = (
        text.strip()
        .replace("'", '"')            # quotes simples -> doubles
        .replace("\n", " ")           # une seule ligne
        .replace("”", '"').replace("“", '"')  # éventuelles quotes typographiques
    )

    try:
        data = json.loads(normalized)
    except json.JSONDecodeError:
        # Cas rare: certains modèles renvoient du texte extra; on tente d'isoler le bloc {...}
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(normalized[start:end+1])
        else:
            raise ValueError(f"Réponse non JSON: {text!r}")

    # Validation du schéma
    if not isinstance(data, dict) or "mood" not in data:
        raise ValueError(f"Clé 'mood' absente: {data!r}")

    mood = data["mood"]
    if mood not in ("Happy", "Sad"):
        raise ValueError(f"Valeur 'mood' invalide (attendu 'Happy' ou 'Sad'): {mood!r}")

    # On ne renvoie que ce qui est attendu
    return MoodDict(mood=mood)


# --- 4) Chaîne LCEL : prompt -> LLM -> texte -> validation -> dict Python ---
chain = (
    prompt
    | model
    | StrOutputParser()
    | RunnableLambda(_strict_json_validator)
)

# %% colab={"base_uri": "https://localhost:8080/"} id="6jMhUhiU5D-s" outputId="708c0dfe-4751-4570-a187-416011464514"
chain.invoke({"message": "Je vais t'obliger à faire mon travail !"})

# %% id="WbzggmkdY9Em"
from typing_extensions import TypedDict

class State(TypedDict):
    graph_state: str
    mood: str

def node_Prompt(state):
    print("---Node Prompt---")
    print({"graph_state": state['graph_state']})
    return {"graph_state": state['graph_state']}

def node_HAPPY(state):
    print("---Node HAPPY---")
    return {"graph_state": "Le message qui a été formulé semble super HAPPY !"}

def node_SAD(state):
    print("---Node SAD---")
    return {"graph_state": "Le message qui a été formulé semble super SAD !"}

def decide_mood(state) -> Literal["node_HAPPY", "node_SAD"]:
    json_mood = chain.invoke({"message": state['graph_state']})
    state['mood'] = json_mood['mood']
    if state['mood'] == "Sad":
      return "node_SAD"
    if state['mood'] == "Happy":
      return "node_HAPPY"

from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

# Build graph
builder = StateGraph(State)
builder.add_node("node_Prompt", node_Prompt)
builder.add_node("node_HAPPY", node_HAPPY)
builder.add_node("node_SAD", node_SAD)

# Logic
builder.add_edge(START, "node_Prompt")
builder.add_conditional_edges("node_Prompt", decide_mood)
builder.add_edge("node_HAPPY", END)
builder.add_edge("node_SAD", END)

# Add
graph_mood = builder.compile()

# %% colab={"base_uri": "https://localhost:8080/"} id="JQ7H-yoVgS-p" outputId="22f0c24d-abe9-444a-f3b9-ee2b948da88c"
graph_mood.invoke({"graph_state" : "Bonjour, vous allez bien ?"})

# %% [markdown] id="Juaxe9FkkUhn"
# # Chaîne
#
# ## Récapitulatif
#
# Nous avons construit un graphe simple avec des nœuds, des arêtes normales et des arêtes conditionnelles.
#
# ## Objectifs
#
# Construisons maintenant une chaîne simple qui combine 4 [concepts](https://python.langchain.com/v0.2/docs/concepts/) :
#
# * Utiliser les [messages de chat](https://python.langchain.com/v0.2/docs/concepts/#messages) comme état de notre graphe
# * Utiliser les [modèles de chat](https://python.langchain.com/v0.2/docs/concepts/#chat-models) dans les nœuds du graphe
# * [Lier des outils](https://python.langchain.com/v0.2/docs/concepts/#tools) à notre modèle de chat
# * [Exécuter des appels d’outils](https://python.langchain.com/v0.2/docs/concepts/#functiontool-calling) dans les nœuds du graphe
#
# ![Capture d’écran 2024-08-21 à 09.24.03.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbab08dd607b08df5e1101_chain1.png)
#

# %% id="7NenGrVJjlOl"
# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langgraph

# %% [markdown] id="ZFmWqk1pkjvZ"
# ## Messages
#
# Les modèles de chat peuvent utiliser des [`messages`](https://python.langchain.com/v0.2/docs/concepts/#messages), qui représentent différents rôles dans une conversation.
#
# LangChain prend en charge plusieurs types de messages, notamment `HumanMessage`, `AIMessage`, `SystemMessage` et `ToolMessage`.
#
# Ceux-ci correspondent respectivement à un message provenant de l'utilisateur, du modèle de chat, d'instructions données au modèle de chat, et d'un appel d'outil.
#
# Créons une liste de messages.
#
# Chaque message peut contenir plusieurs éléments :
#
# * `content`: le contenu du message
# * `name`: facultatif, un auteur du message
# * `response_metadata`: facultatif, un dictionnaire de métadonnées (par exemple, souvent renseigné par le fournisseur du modèle pour les `AIMessages`)
#

# %% colab={"base_uri": "https://localhost:8080/"} id="kZXwASS1ku9Z" outputId="5d86b0b8-8409-4d71-8e39-d2eb0a1fb108"
from pprint import pprint
from langchain_core.messages import AIMessage, HumanMessage

messages = [AIMessage(content=f"So you said you were researching ocean mammals?", name="Model")]
messages.append(HumanMessage(content=f"Yes, that's right.", name="Lance"))
messages.append(AIMessage(content=f"Great, what would you like to learn about.", name="Model"))
messages.append(HumanMessage(content=f"I want to learn about the best place to see Orcas in the US.", name="Lance"))

for m in messages:
    m.pretty_print()

# %% [markdown] id="4WYBpZaXk688"
# ## Modèles de chat
#
# Les [modèles de chat](https://python.langchain.com/v0.2/docs/concepts/#chat-models) peuvent utiliser une séquence de messages comme entrée et prennent en charge différents types de messages, comme mentionné ci-dessus.
#
# Il en existe [de nombreux](https://python.langchain.com/v0.2/docs/concepts/#chat-models) parmi lesquels choisir ! Travaillons avec OpenAI.
#
# Vérifions que votre `OPENAI_API_KEY` est bien défini et, si ce n'est pas le cas, vous serez invité à le saisir.
#

# %% id="i5Of86j9k0hJ" colab={"base_uri": "https://localhost:8080/"} outputId="d6c125ee-6a87-4965-c74c-5a813e049900"
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

# %% [markdown] id="cUQBOP2qlKIc"
# Nous pouvons charger un modèle de chat et l'invoquer avec notre liste de messages.
#
# Nous voyons que le résultat est un `AIMessage` avec des `response_metadata` spécifiques.
#

# %% colab={"base_uri": "https://localhost:8080/", "height": 187} id="-1pTprjvlATL" outputId="64508bc8-c334-4644-8b35-cc55fe5ab821"
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
result = llm.invoke(messages)
type(result)

# %% colab={"base_uri": "https://localhost:8080/"} id="nomVH6nwlPgt" outputId="67dcbb04-927a-4252-b0cf-42e2cf758741"
result

# %% colab={"base_uri": "https://localhost:8080/"} id="oHN2wnfhlSjs" outputId="305e0570-a6ba-4053-8d70-43886c8b7273"
result.response_metadata


# %% [markdown] id="rFDkBmOBliPk"
# ## Outils
#
# Les outils sont utiles chaque fois que vous souhaitez qu'un modèle interagisse avec des systèmes externes.
#
# Les systèmes externes (par exemple, des API) exigent souvent un schéma d'entrée ou une charge utile spécifique, plutôt qu'un langage naturel.
#
# Lorsque nous lions une API, par exemple en tant qu'outil, nous donnons au modèle la connaissance du schéma d'entrée requis.
#
# Le modèle choisira alors d'appeler un outil en fonction de l'entrée en langage naturel de l'utilisateur.
#
# Et il retournera une sortie qui respecte le schéma de l'outil.
#
# [De nombreux fournisseurs de LLM prennent en charge l'appel d'outils](https://python.langchain.com/v0.1/docs/integrations/chat/) et l'[interface d'appel d'outils](https://blog.langchain.dev/improving-core-tool-interfaces-and-docs-in-langchain/) dans LangChain est simple.
#
# Vous pouvez simplement passer n'importe quelle `function` Python dans `ChatModel.bind_tools(function)`.
#
# ![Capture d'écran 2024-08-19 à 19.46.28.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbab08dc1c17a7a57f9960_chain2.png)
#

# %% id="-MZ3CpHKlUxq"
def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

llm_with_tools = llm.bind_tools([multiply])

# %% [markdown] id="K0OinczVl47W"
# Si nous passons une entrée — par exemple, `"What is 2 multiplied by 3"` — nous voyons qu'un appel d'outil est renvoyé.
#
# L'appel d'outil contient des arguments spécifiques qui correspondent au schéma d'entrée de notre fonction, ainsi que le nom de la fonction à appeler.
#
# ```
# {'arguments': '{"a":2,"b":3}', 'name': 'multiply'}
# ```

# %% id="4ZQvGIGzlzjK"
tool_call = llm_with_tools.invoke([HumanMessage(content=f"What is 2 multiplied by 3", name="Lance")])

# %% colab={"base_uri": "https://localhost:8080/"} id="AJsVqbL1l-vs" outputId="9e887464-8549-4df2-a906-1df701fb599f"
tool_call

# %% [markdown] id="J0AzM3kTmGqD"
# ## Utiliser les messages comme état
#
# Avec ces bases en place, nous pouvons maintenant utiliser les [`messages`](https://python.langchain.com/v0.2/docs/concepts/#messages) dans l'état de notre graphe.
#
# Définissons notre état, `MessagesState`, comme un `TypedDict` avec une seule clé : `messages`.
#
# `messages` est simplement une liste de messages, comme nous l'avons défini plus haut (par exemple, `HumanMessage`, etc.).
#

# %% id="V5wJ2ynXmAS6"
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage

class MessagesState(TypedDict):
    messages: list[AnyMessage]


# %% [markdown] id="WyZd2KG9mPJc"
# ## Réducteurs
#
# Nous avons maintenant un petit problème !
#
# Comme nous l'avons vu, chaque nœud retournera une nouvelle valeur pour notre clé d'état `messages`.
#
# Mais cette nouvelle valeur [remplacera](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) la valeur précédente de `messages`.
#
# Or, lors de l'exécution de notre graphe, nous voulons **ajouter** des messages à notre clé d'état `messages`.
#
# Pour résoudre cela, nous pouvons utiliser des [fonctions réductrices](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers).
#
# Les réducteurs nous permettent de spécifier comment les mises à jour de l'état sont effectuées.
#
# Si aucune fonction réductrice n'est spécifiée, alors on suppose que les mises à jour de la clé doivent *la remplacer*, comme nous l'avons vu précédemment.
#
# Mais, pour ajouter des messages, nous pouvons utiliser le réducteur préconstruit `add_messages`.
#
# Cela garantit que tous les nouveaux messages sont ajoutés à la liste existante de messages.
#
# Il nous suffit simplement d'annoter notre clé `messages` avec la fonction réductrice `add_messages` en tant que métadonnée.
#

# %% id="jn1NxM5cmMKL"
from typing import Annotated
from langgraph.graph.message import add_messages

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# %% [markdown] id="bbWtBvLCmoDn"
# Comme avoir une liste de messages dans l'état du graphe est très courant, LangGraph propose un [`MessagesState`](https://langchain-ai.github.io/langgraph/concepts/low_level/#messagesstate) déjà prêt à l'emploi !
#
# `MessagesState` est défini ainsi :
#
# * Avec une clé unique `messages` prédéfinie
# * Cette clé contient une liste d'objets `AnyMessage`
# * Il utilise le réducteur `add_messages`
#
# Nous utiliserons généralement `MessagesState` car il est moins verbeux que de définir un `TypedDict` personnalisé, comme montré ci-dessus.
#

# %% id="t1dungt8mg4c"
from langgraph.graph import MessagesState

class MessagesState(MessagesState):
    # Add any keys needed beyond messages, which is pre-built
    pass


# %% [markdown] id="gdU2h1_6m2Ll"
# Pour aller un peu plus loin, nous pouvons voir comment le réducteur `add_messages` fonctionne de manière isolée.
#

# %% colab={"base_uri": "https://localhost:8080/", "height": 216} id="WrBQ1wk1mwEc" outputId="d39100d3-db0f-45cd-d8c2-b8fad0b852ac"
# Initial state
initial_messages = [AIMessage(content="Hello! How can I assist you?", name="Model"),
                    HumanMessage(content="I'm looking for information on marine biology.", name="Lance")
                   ]

# New message to add
new_message = AIMessage(content="Sure, I can help with that. What specifically are you interested in?", name="Model")

# Test
add_messages(initial_messages , new_message)

# %% [markdown] id="h6KyOGM7nJWF"
# ## Notre graphe
#
# Utilisons maintenant `MessagesState` avec un graphe.
#

# %% colab={"base_uri": "https://localhost:8080/", "height": 251} id="p1jD6J0_m439" outputId="b658eafa-f29c-4e04-fd15-256cf5815d88"
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_edge(START, "tool_calling_llm")
builder.add_edge("tool_calling_llm", END)
graph = builder.compile()

# View
display(Image(graph.get_graph().draw_mermaid_png()))

# %% [markdown] id="J6lfx_9knS3C"
# Si nous passons `Hello!`, le LLM répond sans aucun appel d'outil.

# %% colab={"base_uri": "https://localhost:8080/"} id="_vQhRa6wnMZf" outputId="b364c233-b2fc-41d0-ab26-9d31503936c7"
messages = graph.invoke({"messages": HumanMessage(content="Hello!")})
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="vPvv-aGnnecq"
# Le LLM choisit d'utiliser un outil lorsqu'il détermine que l'entrée ou la tâche nécessite la fonctionnalité fournie par cet outil.

# %% colab={"base_uri": "https://localhost:8080/"} id="mPwa7F6EnW0B" outputId="35f38513-3843-4be4-fee3-8e1af74c1396"
messages = graph.invoke({"messages": HumanMessage(content="Multiply 2 and 3")})
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="q6xmCGI3n-kE"
# # Routeur
#
# ## Récapitulatif
#
# Nous avons construit un graphe qui utilise `messages` comme état et un modèle de chat avec des outils liés.
#
# Nous avons vu que le graphe peut :
#
# * Retourner un appel d'outil
# * Retourner une réponse en langage naturel
#
# ## Objectifs
#
# Nous pouvons voir cela comme un routeur, où le modèle de chat oriente entre une réponse directe ou un appel d'outil en fonction de l'entrée de l'utilisateur.
#
# Ceci est un exemple simple d'agent, où le LLM dirige le flux de contrôle soit en appelant un outil, soit en répondant directement.
#
# ![Capture d'écran 2024-08-21 à 09.24.09.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbac6543c3d4df239a4ed1_router1.png)
#
# Étendons notre graphe pour qu'il fonctionne avec l'une ou l'autre sortie !
#
# Pour cela, nous pouvons utiliser deux idées :
#
# 1. Ajouter un nœud qui appellera notre outil.
# 2. Ajouter une arête conditionnelle qui examinera la sortie du modèle de chat et orientera soit vers notre nœud d'appel d'outil, soit vers la fin si aucun appel d'outil n'est effectué.

# %% id="AplBkqmbnjey"
# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langgraph langgraph-prebuilt

# %% id="vB3ezjKmoSsV"
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

# %% id="0RXE6sDzoVaU"
from langchain_openai import ChatOpenAI

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([multiply])

# %% [markdown] id="q7ECn0KWocPl"
# Nous utilisons le [`ToolNode` intégré](https://langchain-ai.github.io/langgraph/reference/prebuilt/?h=tools+condition#toolnode) et nous lui passons simplement une liste de nos outils pour l'initialiser.
#
# Nous utilisons le [`tools_condition` intégré](https://langchain-ai.github.io/langgraph/reference/prebuilt/?h=tools+condition#tools_condition) comme notre arête conditionnelle.
#

# %% id="3HyUlt89oWu0" outputId="4a416e27-368f-4f30-fced-e1e3959426b3" colab={"base_uri": "https://localhost:8080/", "height": 350}
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode([multiply]))
builder.add_edge(START, "tool_calling_llm")
builder.add_conditional_edges(
    "tool_calling_llm",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", END)
graph = builder.compile()

# View
display(Image(graph.get_graph().draw_mermaid_png()))

# %% id="jQYqwBy2ojl3" outputId="49e54433-2839-4399-f7b0-95d13d138a4f" colab={"base_uri": "https://localhost:8080/"}
from langchain_core.messages import HumanMessage
messages = [HumanMessage(content="Hello, what is 2 multiplied by 2?")]
messages = graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="Cnn2A6DBp7eB"
# # Agent
#
# ## Récapitulatif
#
# Nous avons construit un routeur.
#
# * Notre modèle de chat décide de faire ou non un appel d'outil en fonction de l'entrée de l'utilisateur
# * Nous utilisons une arête conditionnelle pour orienter vers un nœud qui appellera notre outil ou terminera simplement
#
# ![Capture d'écran 2024-08-21 à 12.44.33.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbac0ba0bd34b541c448cc_agent1.png)
#
# ## Objectifs
#
# Nous pouvons maintenant étendre cela vers une architecture d'agent générique.
#
# Dans le routeur ci-dessus, nous invoquions le modèle et, s'il choisissait d'appeler un outil, nous retournions un `ToolMessage` à l'utilisateur.
#
# Mais, que se passe-t-il si nous renvoyons simplement ce `ToolMessage` *au modèle* ?
#
# Nous pouvons alors le laisser soit (1) appeler un autre outil, soit (2) répondre directement.
#
# C'est l'intuition derrière [ReAct](https://react-lm.github.io/), une architecture d'agent générale.
#
# * `act`: laisser le modèle appeler des outils spécifiques
# * `observe`: renvoyer la sortie de l'outil au modèle
# * `reason`: laisser le modèle raisonner sur la sortie de l'outil pour décider de la suite (par ex., appeler un autre outil ou simplement répondre directement)
#
# Cette [architecture polyvalente](https://blog.langchain.dev/planning-for-agents/) peut être appliquée à de nombreux types d'outils.
#
# ![Capture d'écran 2024-08-21 à 12.45.43.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbac0b4a2c1e5e02f3e78b_agent2.png)
#

# %% id="xReIPvQQorBE"
# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langgraph langgraph-prebuilt

# %% id="tpSRLmvvqWTX"
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

# %% [markdown] id="k-m8Au-Tq1cY"
# Ici, nous allons utiliser [LangSmith](https://docs.smith.langchain.com/) pour le [tracing](https://docs.smith.langchain.com/concepts/tracing).
#
# Nous enregistrerons les journaux dans un projet nommé `langchain-academy`.

# %% colab={"base_uri": "https://localhost:8080/"} id="vIntxlJFqY3I" outputId="c55c5ce6-1eee-4e1b-f4d2-02882ce01e11"
_set_env("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "langchain-academy"

# %% id="kMNtH5syq40n"
from langchain_openai import ChatOpenAI

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# This will be a tool
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b

def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]
llm = ChatOpenAI(model="gpt-4o")

# For this ipynb we set parallel tool calling to false as math generally is done sequentially, and this time we have 3 tools that can do math
# the OpenAI model specifically defaults to parallel tool calling for efficiency, see https://python.langchain.com/docs/how_to/tool_calling_parallel/
# play around with it and see how the model behaves with math equations!
llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

# %% [markdown] id="Ku8JRf8prBdz"
# Créons notre LLM et donnons-lui un prompt décrivant le comportement global souhaité de l'agent.

# %% id="97XSjGyIq8E7"
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")

# Node
def assistant(state: MessagesState):
  print(state["messages"])
  return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


# %% [markdown] id="aJ7tyFnMrKpT"
# Comme précédemment, nous utilisons `MessagesState` et définissons un nœud `Tools` avec notre liste d'outils.
#
# Le nœud `Assistant` est simplement notre modèle avec les outils liés.
#
# Nous créons un graphe avec les nœuds `Assistant` et `Tools`.
#
# Nous ajoutons une arête `tools_condition`, qui oriente vers `End` ou vers `Tools` selon que l'`Assistant` appelle un outil ou non.
#
# Nous ajoutons maintenant une nouvelle étape :
#
# Nous connectons le nœud `Tools` *de nouveau* à l'`Assistant`, formant ainsi une boucle.
#
# * Après l'exécution du nœud `Assistant`, `tools_condition` vérifie si la sortie du modèle est un appel d'outil.
# * Si c'est un appel d'outil, le flux est dirigé vers le nœud `Tools`.
# * Le nœud `Tools` se connecte de nouveau à `Assistant`.
# * Cette boucle continue tant que le modèle choisit d'appeler des outils.
# * Si la réponse du modèle n'est pas un appel d'outil, le flux est dirigé vers `END`, ce qui termine le processus.
#

# %% colab={"base_uri": "https://localhost:8080/", "height": 266} id="dwed4rserFRc" outputId="835548af-29dd-4aea-a7bb-a4a565a6a81e"
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from IPython.display import Image, display

# Graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")
react_graph = builder.compile()

# Show
display(Image(react_graph.get_graph(xray=True).draw_mermaid_png()))

# %% id="Wv7xLnQlrVhe" colab={"base_uri": "https://localhost:8080/"} outputId="9221a6ce-0c79-465c-d518-d3ed3e186f62"
messages = [HumanMessage(content="3+4*2+4/3")]
messages = react_graph.invoke({"messages": messages})

# %% colab={"base_uri": "https://localhost:8080/"} id="UjQ_iTHQrYDd" outputId="d96f67f0-dbdf-4514-998d-d30bf9de4fd4"
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="rA-YNNHKsZdf"
# # Mémoire de l'agent
#
# ## Récapitulatif
#
# Précédemment, nous avons construit un agent capable de :
#
# * `act`: laisser le modèle appeler des outils spécifiques
# * `observe`: renvoyer la sortie de l'outil au modèle
# * `reason`: laisser le modèle raisonner sur la sortie de l'outil pour décider de la suite (par ex., appeler un autre outil ou simplement répondre directement)
#
# ![Capture d'écran 2024-08-21 à 12.45.32.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbab7453080e6802cd1703_agent-memory1.png)
#
# ## Objectifs
#
# Nous allons maintenant étendre notre agent en lui ajoutant une mémoire.
#

# %% id="XFt-1dFRraX-"
# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langgraph langgraph-prebuilt

# %% id="fS7_v_dHsieR"
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

# %% id="e17hF4_rskdS"
_set_env("LANGSMITH_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "langchain-academy"

# %% id="kL9Q5Os4sm1P"
from langchain_openai import ChatOpenAI

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# This will be a tool
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b

def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

# %% id="E1f79__4sqGQ"
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


# %% colab={"base_uri": "https://localhost:8080/", "height": 266} id="li5YvEe8ssMP" outputId="3adc8977-7658-4c8c-d9a7-bb102d59fce0"
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from IPython.display import Image, display

# Graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")
react_graph = builder.compile()

# Show
display(Image(react_graph.get_graph(xray=True).draw_mermaid_png()))

# %% [markdown] id="ZiMoqE4ss0DM"
# ## Mémoire
#
# Exécutons notre agent, comme précédemment.
#

# %% colab={"base_uri": "https://localhost:8080/"} id="74tr3_f8stxh" outputId="ec9ada8e-a7b5-4450-ca56-b32e11d93dd3"
messages = [HumanMessage(content="Add 3 and 4.")]
messages = react_graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="VUIt0pfxs_Ly"
# Maintenant, multiplions par 2 !

# %% colab={"base_uri": "https://localhost:8080/"} id="7r2FaQDzs31A" outputId="23dee6e0-d584-4f56-f31e-cfd898d75d43"
messages = [HumanMessage(content="Multiply that by 2.")]
messages = react_graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="RqZHUjvptY-k"
# Nous ne conservons pas en mémoire le `7` de notre discussion initiale !
#
# C'est parce que [l'état est transitoire](https://github.com/langchain-ai/langgraph/discussions/352#discussioncomment-9291220) à une seule exécution du graphe.
#
# Bien sûr, cela limite notre capacité à avoir des conversations multi-tours avec interruptions.
#
# Nous pouvons utiliser la [persistance](https://langchain-ai.github.io/langgraph/how-tos/persistence/) pour résoudre ce problème !
#
# LangGraph peut utiliser un *checkpointer* pour sauvegarder automatiquement l'état du graphe après chaque étape.
#
# Cette couche de persistance intégrée nous donne une mémoire, permettant à LangGraph de reprendre à partir de la dernière mise à jour de l'état.
#
# L'un des *checkpointers* les plus simples à utiliser est le `MemorySaver`, un stockage clé-valeur en mémoire pour l'état du graphe.
#
# Il nous suffit simplement de compiler le graphe avec un *checkpointer*, et notre graphe dispose d'une mémoire !
#

# %% id="ARgwp_W8tBJi"
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
react_graph_memory = builder.compile(checkpointer=memory)

# %% [markdown] id="khzPFSLEtlDD"
# Lorsque nous utilisons la mémoire, nous devons spécifier un `thread_id`.
#
# Ce `thread_id` stockera notre collection d'états du graphe.
#
# Voici un schéma explicatif :
#
# * Le *checkpointer* écrit l'état à chaque étape du graphe
# * Ces checkpoints sont sauvegardés dans un thread
# * Nous pouvons accéder à ce thread plus tard en utilisant le `thread_id`
#
# ![state.jpg](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66e0e9f526b41a4ed9e2d28b_agent-memory2.png)
#

# %% id="wM60Ig4otgBy" outputId="2c773412-0c1e-484f-a934-3c27b155eb50" colab={"base_uri": "https://localhost:8080/"}
# Specify a thread
config = {"configurable": {"thread_id": "1"}}

# Specify an input
messages = [HumanMessage(content="Add 3 and 4.")]

# Run
messages = react_graph_memory.invoke({"messages": messages},config)
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="PY7gquiOtxGl"
# Si nous passons le même `thread_id`, alors nous pouvons reprendre à partir du dernier état enregistré en checkpoint !
#
# Dans ce cas, la conversation ci-dessus est conservée dans le thread.
#
# Le `HumanMessage` que nous passons (`"Multiply that by 2."`) est ajouté à la conversation précédente.
#
# Ainsi, le modèle sait maintenant que `that` fait référence à `La somme de 3 et 4 est 7.`

# %% id="UBGXXtRQtraX" outputId="99eff154-fd3e-4946-8d81-d235057020cb" colab={"base_uri": "https://localhost:8080/"}
messages = [HumanMessage(content="Multiply that by 2.")]
messages = react_graph_memory.invoke({"messages": messages}, config)
for m in messages['messages']:
    m.pretty_print()

# %% [markdown] id="rNxntrZ6uckU"
# ## Application
#
# ### Agent "Web-Aware" — Application
#
# **But :** proposer un agent LLM qui répond directement quand il sait — et **déclenche une recherche Internet** quand la demande est **récente / sujette à mise à jour** (prix, lois, actualités, résultats sportifs, météo, versions logicielles…) ou quand l'info **n'est pas dans sa base de connaissances** implicite.
#
# On réutilise la même structure qu'au-dessus : `MessagesState` ➜ nœud `assistant` (LLM outillant) ➜ `ToolNode` ➜ arêtes conditionnelles via `tools_condition` ➜ `MemorySaver`.

# %% id="Lo9RjIb9t1OS"
# (1) Dépendances & clés API (réutilise _set_env défini plus haut)
# %%capture --no-stderr
# %pip install -q -U langchain_community tavily-python

# Clés API (déjà fait pour OPENAI ci-dessus)
_set_env("TAVILY_API_KEY")

# %% id="dWVwiYYMwhKQ"
# (2) Outil: recherche Web via Tavily
from typing import List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults

def web_search(query: str, k: int = 5) -> str:
    """Recherche Internet (Tavily).

    À utiliser pour:
    - sujets récents (≤ ~18 mois), informations temporelles (prix, lois, horaires);
    - actualités, résultats, météo, versions logicielles, événements en direct;
    - vérifications factuelles quand l'information est incertaine ou absente.

    Args:
        query: requête de recherche
        k: nombre maximum de résultats
    """
    tavily = TavilySearchResults(max_results=k)
    results: List[Dict[str, Any]] = tavily.invoke(query)
    if not results:
        return "Aucun résultat trouvé."
    lines = []
    for r in results:
        title = r.get("title") or ""
        url = r.get("url") or r.get("source") or ""
        snippet = r.get("content") or ""
        if len(snippet) > 260:
            snippet = snippet[:257] + "…"
        lines.append(f"- {title} — {snippet} (source: {url})")
    return "\n".join(lines)


# %% id="gHMdBhC0wlC6"
# (3) Agent: LLM outillé qui décide quand chercher en ligne
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import MessagesState, START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.checkpoint.memory import MemorySaver

# LLM + outils
web_tools = [web_search]
web_llm = ChatOpenAI(model="gpt-4o", temperature=0)
web_llm_with_tools = web_llm.bind_tools(web_tools)

WEB_SYS = SystemMessage(content=(
    "Tu es un agent utile et factuel. "
    "Réponds directement quand tu sais avec confiance. "
    "Si la question est récente, temporelle, sujette à mise à jour, "
    "ou si tu n'es pas sûr que l'information soit dans ta base de connaissances, "
    "APPELLE l'outil `web_search` avec une requête claire et spécifique. "
    "Après recherche, synthétise la réponse en français et indique les sources (URLs)."
))

def web_assistant(state: MessagesState):
    # On préprend le message système et on laisse le LLM décider d'appeler ou non l'outil
    msgs = [WEB_SYS] + state["messages"]
    return {"messages": [web_llm_with_tools.invoke(msgs)]}

# Graphe
web_builder = StateGraph(MessagesState)
web_builder.add_node("assistant", web_assistant)
web_builder.add_node("tools", ToolNode(web_tools))

# Arêtes
web_builder.add_edge(START, "assistant")
web_builder.add_conditional_edges("assistant", tools_condition)  # si tool call -> "tools" sinon -> END
web_builder.add_edge("tools", "assistant")

# Mémoire de thread (permet le suivi de conversation)
web_memory = MemorySaver()
web_graph = web_builder.compile(checkpointer=web_memory)

# Config thread
web_config = {"configurable": {"thread_id": "application-web-aware"}}

def ask(user_text: str):
    """Petit helper pour interroger l'agent Web-Aware."""
    res = web_graph.invoke({"messages": [HumanMessage(content=user_text)]}, web_config)
    return res


# %% colab={"base_uri": "https://localhost:8080/"} id="wHYXC5yswlzb" outputId="7a8175c3-f39b-4369-f442-16ac362f6c0b"
# (4) Démo
# Exemple "récent" -> devrait déclencher une recherche
resp = ask("Qui est le/la Ministre de l'Économie en France actuellement en août 2025 ? Cite tes sources.")
for m in resp["messages"]:
  m.pretty_print()

# Exemple "connaissance générale" -> souvent sans recherche
# resp = ask("Explique brièvement ce qu'est LangGraph et à quoi il sert.")
# for m in resp["messages"]:
#     m.pretty_print()

# Exemple explicite: prix/scores (doit chercher)
# resp = ask("Quel est le score du dernier match de l'équipe de France de football ?")
# for m in resp["messages"]:
#     m.pretty_print()

# %% [markdown] id="8rPb7cjujFjD"
# # Case study (2/2) — Customer Support Agent avec LangGraph
#
# Cette section illustre **la construction d'un graphe simple pour un système de support client** avec [LangGraph].  
# Objectif : router une demande utilisateur vers la bonne action (**FAQ**, **création de ticket**, ou **escalade vers un humain**) et produire une **réponse finale**.
#
# **Architecture du graphe**  
# - `classify` : détecte une **intention** (faq / refund / tech_issue / other) et une **valence** (calm / frustrated / angry).  
# - `search_kb` : effectue une recherche rapide dans une **base de connaissance** (FAQ).  
# - `create_ticket` : ouvre un **ticket** pour les demandes nécessitant un suivi (remboursement, problème technique).  
# - `draft_reply` : génère une **réponse** claire et actionnable pour l'utilisateur.  
# - `escalate` : prépare un **message d’escalade** quand l’utilisateur est très mécontent.
#
# Le graphe part de `START` → `classify`, puis suit un **router conditionnel** :
# - Si *angry* → `escalate` → `END`
# - Si *faq* → `search_kb` → `draft_reply` → `END`
# - Si *refund* ou *tech_issue* → `create_ticket` → `draft_reply` → `END`
# - Sinon → `draft_reply` → `END`
#
# > Remarque : le code est autonome (règles simples) pour fonctionner **sans LLM**. Vous pouvez remplacer les heuristiques par des appels LLM si besoin.
#

# %% [markdown] id="8co1HwGKjL71"
# > 💡 **Dépendances**  
# Ce notebook suppose que `langgraph` est installé. Si nécessaire :
# ```bash
# pip install -U langgraph langchain-core
# ```
# (ou ajoutez les intégrations LLM / vecteurs de votre choix)
#

# %% id="4Ya3WaijjHpJ"
# --- Définition de l'état et d'une mini base de connaissances FAQ ---
from typing import TypedDict, Literal, Optional, List, Tuple
import uuid
import re

class SupportState(TypedDict):
    user_message: str
    intent: Optional[Literal["faq", "refund", "tech_issue", "other"]]
    sentiment: Optional[Literal["calm", "frustrated", "angry"]]
    kb_results: Optional[List[str]]
    ticket_id: Optional[str]
    reply: Optional[str]
    history: List[Tuple[str, str]]  # (role, content)

# Mini base de connaissances (à remplacer par un vrai retriever / vector store)
FAQ = {
    "refund": [
        "Les remboursements sont possibles sous 30 jours après l'achat avec la preuve d'achat.",
        "Le délai de traitement d'un remboursement est de 5 à 10 jours ouvrés."
    ],
    "tech_issue": [
        "Essayez de vider le cache et de redémarrer l'application.",
        "Vérifiez votre connexion internet et mettez l'application à jour."
    ],
    "delivery": [
        "La livraison standard prend 3 à 5 jours ouvrés en France.",
        "Vous pouvez suivre votre colis via le lien de suivi reçu par e-mail."
    ],
    "account": [
        "Pour réinitialiser votre mot de passe, utilisez le lien 'Mot de passe oublié'.",
        "La double authentification est disponible dans les paramètres de sécurité."
    ]
}


# %% id="oQMDv-ksjOJ0"
# --- Heuristiques simples pour l'intention et la valence (sans LLM) ---
INTENT_RULES = [
    (r"\b(remboursement|refund|rembourser|retour)\b", "refund"),
    (r"\b(bug|erreur|probl[eè]me|technique|crash)\b", "tech_issue"),
    (r"\b(livraison|colis|suivi|deliv|delivery|exp[ée]dition)\b", "faq"),
    (r"\b(compte|password|mot de passe|2fa|authentification)\b", "faq"),
]

SENTIMENT_RULES = [
    (r"\b(scandale|inadmissible|honte|furieux|angry|rage|inacceptable)\b", "angry"),
    (r"\b(m[eê]content|pas content|frustr[éee]|agac[éee])\b", "frustrated"),
]

def classify_intent_and_sentiment(state: 'SupportState') -> 'SupportState':
    text = state['user_message'].lower()
    intent = None
    for pattern, label in INTENT_RULES:
        if re.search(pattern, text):
            intent = label if label in ("refund", "tech_issue") else "faq"
            break
    if intent is None:
        intent = "other"

    sentiment = "calm"
    for pattern, label in SENTIMENT_RULES:
        if re.search(pattern, text):
            sentiment = label
            break

    state['intent'] = intent
    state['sentiment'] = sentiment
    return state



# %% id="8OjYKoeQjjFC"
# --- Définition des noeuds de traitement ---
def search_kb(state: 'SupportState') -> 'SupportState':
    text = state['user_message'].lower()
    results: list[str] = []
    # Recherche naïve par mots-clés
    for topic, entries in FAQ.items():
        if topic in text or any(word in text for word in ["livraison","delivery","colis","suivi","account","compte","password","mot de passe"]):
            results.extend(entries)
    # Si aucune correspondance forte, fallback sur l'intention
    if not results and state.get('intent') == 'faq':
        for entries in FAQ.values():
            results.extend(entries[:1])  # un échantillon
    state['kb_results'] = results[:5] if results else None
    return state

def create_ticket(state: 'SupportState') -> 'SupportState':
    # Génère un identifiant de ticket
    state['ticket_id'] = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    return state

def draft_reply(state: 'SupportState') -> 'SupportState':
    intent = state.get('intent')
    sentiment = state.get('sentiment', 'calm')
    kb = state.get('kb_results') or []
    ticket = state.get('ticket_id')

    parts = []
    # Tonalité
    if sentiment in ("frustrated","angry"):
        parts.append("Je suis désolé(e) pour la gêne occasionnée et je comprends votre frustration.")
    else:
        parts.append("Merci pour votre message !")

    # Corps en fonction du flux
    if intent == 'faq' and kb:
        parts.append("Voici quelques informations qui devraient vous aider :")
        parts.extend(f"- {k}" for k in kb)
        parts.append("Si cela ne répond pas complètement à votre question, dites-le moi et je pourrai ouvrir un ticket.")
    elif intent in ("refund","tech_issue") and ticket:
        if intent == "refund":
            parts.append("J’ai ouvert un ticket de remboursement pour vous.")
        else:
            parts.append("J’ai ouvert un ticket pour votre problème technique.")
        parts.append(f"Identifiant du ticket : **{ticket}**.")
        parts.append("Notre équipe vous recontactera sous 24–48 h. En attendant, n’hésitez pas à donner tout détail complémentaire.")
    else:
        # Fallback générique
        parts.append("Pouvez-vous préciser votre demande ? Je peux soit vous donner des infos utiles, soit ouvrir un ticket si nécessaire.")

    state['reply'] = " \n".join(parts)
    # Maintenir un historique minimal
    hist = state.get('history', [])
    hist = hist + [("assistant", state['reply'])]
    state['history'] = hist
    return state

def escalate_to_human(state: 'SupportState') -> 'SupportState':
    msg = [
        "Je suis navré(e) pour la situation. Je vais transmettre immédiatement votre demande à un agent humain.",
        "Vous serez recontacté(e) en priorité. Merci pour votre patience."
    ]
    state['reply'] = " \n".join(msg)
    hist = state.get('history', [])
    hist = hist + [("assistant", state['reply'])]
    state['history'] = hist
    return state



# %% colab={"base_uri": "https://localhost:8080/"} id="dj9l4hf3jkyM" outputId="d0faa9c2-8fc8-4741-8a00-7f417eadc232"
# --- Construction du graphe LangGraph ---
from langgraph.graph import StateGraph, START, END

def router(state: 'SupportState') -> str:
    # Retourne une étiquette correspondant aux arêtes conditionnelles
    if state.get('sentiment') == 'angry':
        return 'escalate'
    intent = state.get('intent')
    if intent == 'faq':
        return 'faq'
    if intent in ('refund','tech_issue'):
        return 'ticket'
    return 'draft'

# Déclare le graphe
workflow = StateGraph(SupportState)

# Noeuds
workflow.add_node('classify', classify_intent_and_sentiment)
workflow.add_node('search_kb', search_kb)
workflow.add_node('create_ticket', create_ticket)
workflow.add_node('draft_reply', draft_reply)
workflow.add_node('escalate', escalate_to_human)

# Départ
workflow.add_edge(START, 'classify')

# Routage conditionnel
workflow.add_conditional_edges(
    'classify',
    router,
    {
        'escalate': 'escalate',
        'faq': 'search_kb',
        'ticket': 'create_ticket',
        'draft': 'draft_reply',
    }
)

# Chaînage
workflow.add_edge('search_kb', 'draft_reply')
workflow.add_edge('create_ticket', 'draft_reply')
workflow.add_edge('draft_reply', END)
workflow.add_edge('escalate', END)

# Compile le graphe exécutable
support_graph = workflow.compile()
print("Graphe de support client prêt.")

# %% colab={"base_uri": "https://localhost:8080/"} id="jFviuZ0ojmXP" outputId="6615c426-12a6-4d97-efac-dc663c52ab6f"
# --- Démo rapide : essayez différents messages utilisateurs ---
examples = [
    "Bonjour, je veux un remboursement pour ma commande, je suis très mécontent !",
    "Mon application crash au démarrage, vous pouvez m'aider ?",
    "Comment suivre ma livraison ?",
    "J'ai un souci mais je ne sais pas trop comment l'expliquer."
]

for i, prompt in enumerate(examples, 1):
    state: SupportState = {
        'user_message': prompt,
        'intent': None,
        'sentiment': None,
        'kb_results': None,
        'ticket_id': None,
        'reply': None,
        'history': [('user', prompt)]
    }
    result = support_graph.invoke(state)
    print(f"\n=== Exemple {i} ===")
    print("Utilisateur:", prompt)
    print("Réponse:\n", result['reply'])
    if result.get('ticket_id'):
        print("Ticket:", result['ticket_id'])


# %% [markdown] id="c_h52r4Fj3UB"
# ## Pistes d'amélioration
#
# - **Remplacer les heuristiques** par un **LLM** (via LangChain/LangGraph) pour la classification d’intention/sentiment.
# - **Brancher un vrai retriever** (vecteurs, BM25, etc.) pour `search_kb`.
# - **Ajouter un checkpointer** (mémoire) avec LangGraph pour conserver l’état multi-tours.
# - **Journalisation / traçage** : exporter les transitions de graphe pour l’observabilité.
# - **Politiques d’escalade** plus fines (score de toxicité, priorisation VIP, SLA).
#
# > Cette section constitue un point de départ minimal mais complet pour un **agent de support client** avec LangGraph.
