# ACE-Step pour Mac — MLX

**Une interface complète pour [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) sur Apple Silicon, écrite pour les gens qui font de la musique plutôt que pour ceux qui écrivent du code.**

Des mots en entrée, un morceau en sortie. Tout ce qu'on peut réellement dire au
modèle — description, paroles, durée, tempo, tonalité, métrique, seed — tient
sur une seule page, en clair, avec le compromis écrit **à côté** de chaque
réglage plutôt qu'enterré dans un wiki. Rien ne sort de votre Mac.

[![L'interface](docs/screenshot.png)](docs/screenshot-full.png)

*Une seule page. Cliquer pour la voir en entier.*

> Interface **non officielle**. Elle n'est ni faite par l'équipe ACE-Step ni
> affiliée à elle. Elle ne contient pas le modèle.

**[Installation pas à pas, sans rien supposer sur le Terminal →](INSTALL.md)**
· [This README in English →](README.md)

---

## 🆕 Nouveautés de la 1.7

**La famille XL.** ACE-Step publie une seconde branche, plus grande — 4 milliards
de paramètres contre 1 — et elle est dans le menu des modèles audio, avec son
coût écrit dans l'étiquette : un menu déroulant ne devrait jamais déclencher un
téléchargement de 19 Go en silence. Mesuré ici, et c'était la question ouverte :
**MLX accepte XL.** `[MLX-DiT] Native MLX DiT decoder initialized successfully`,
chargé en 19 secondes, sans quantification et sans délestage. Il n'y a aucune
conversion MLX à aller chercher — ACE-Step construit son décodeur MLX à partir
de la configuration du modèle, donc il suit XL jusqu'à sa taille tout seul.

**L'app dit maintenant ce que MLX a réellement fait**, et non ce que la case
demandait. ACE-Step remet `use_mlx_dit` à False, sans rien casser, quand le
décodeur MLX ne se construit pas — un rendu pouvait donc retomber sur
PyTorch-MPS sans un mot, pendant que le `.txt` à côté affirmait « MLX ». Le
journal dit quel chemin a servi, et le fichier enregistre la vérité.

**Deux boutons pour « où c'est parti ? »** — le dossier de sortie depuis la
barre de lancement, et le morceau en cours d'écoute, sélectionné dans le Finder.

**Gradio mangeait le disque en silence.** Il garde sa propre copie de chaque
fichier servi au navigateur et ne range jamais : trois jours de lots ont laissé
**6,8 Go**. `delete_cache` seul n'y suffit pas — il ne connaît que les fichiers
créés par ce processus-là, donc un redémarrage n'en a effacé aucun. L'app balaie
maintenant le dossier elle-même au démarrage, et seulement un dossier qui
s'appelle littéralement `gradio`.

**Le menu des modèles de langage dit ce que chacun coûte** en gigaoctets, pour
qu'on puisse l'ajouter à la taille du modèle audio et voir si la somme tient sur
sa propre machine, au lieu de lire un chiffre vrai pour celle de l'auteur.

---

## 🤔 Pourquoi cette interface

ACE-Step 1.5 est réjouissant, et il est aussi un peu sauvage. La première chose
qu'on remarque, c'est qu'il est **moins obéissant** que les autres modèles de
musique : on décrit quelque chose de précis, il rend quelque chose de plus
frais et pas tout à fait ce qu'on demandait.

Ce n'est pas un caractère, c'est un réglage. ACE-Step contient un petit modèle
de langage qui **réécrit votre description** avant que le modèle audio ne la
voie. Personne ne vous le dit, et il n'y a pas d'interrupteur évident.

La première chose que fait cette interface, c'est donc de mettre cet
interrupteur sur la page, avec trois positions — dont une qui rend le morceau
**deux fois sur le même seed**, une fois tel que vous l'avez tapé, une fois tel
que le modèle l'a réécrit. On entend enfin ce que la réécriture fabrique.

Le reste suit la même règle : **si un réglage ne fait rien, le dire.** `Steps`
est ignoré par le modèle Turbo — vérifié octet par octet, sortie identique à 8
étapes et à 60 — donc l'étiquette dit *(ignoré par Turbo)* au lieu de vous
laisser y passer un après-midi.

---

## 🎛️ Ce qu'elle fait

**Fabriquer de la musique à partir de mots.** Une description, des paroles
éventuelles, et les contrôles de structure que le modèle accepte vraiment :
une tonalité globale, un tempo (ou une fourchette tirée au sort par morceau),
une métrique, une durée.

**Refaire un morceau existant** (*cover*), avec un curseur qui dit à quel point
on s'en éloigne.

**Retrouver un morceau entièrement.** Chaque rendu écrit un `.txt` à côté de
lui, qui contient **tous** les réglages utilisés. On redépose ce fichier sur la
page et toute l'interface revient dans cet état — seed, description, modèles,
tout. Quelque chose vous plaît sur un test de 30 secondes ? Vous déposez, vous
changez la durée, vous relancez.

**Des lots qui restent modifiables.** Jusqu'à 50 morceaux, et **chaque réglage
est relu au début de chaque morceau**. On change le tempo, la description, même
le modèle, vingt minutes après le début d'un lot de cinquante : le changement
s'applique au morceau suivant. Rien à arrêter ni à relancer.

**Prompts dynamiques et séquentiels**, détectés automatiquement, avec le mode
annoncé sous la case au fur et à mesure que vous tapez.

🎲 **Dynamique.** Une option tirée par rendu, fraîche à chaque fois :

```
a {slow|fast} {piano|guitar} piece, {warm|cold}
```

🔁 **Séquentiel.** Des versions complètes séparées par une ligne de trois
tirets ou plus, utilisées une par morceau, dans l'ordre :

```
première idée
---
deuxième idée
```

**Une différence avec Draw Things, qu'il vaut mieux connaître.** Là-bas, le
nombre d'images est décidé par le nombre de blocs. Ici non : le nombre de
morceaux reste un réglage à part, parce qu'on peut très bien vouloir trois
rendus de chaque version plutôt qu'un seul. Une feuille de vingt versions avec le
curseur sur cinq vous donne donc les cinq premières et rien d'autre.

Pour vous épargner le calcul, **un bouton apparaît sous la case dès qu'un
prompt séquentiel est détecté** — *Set the number of tracks to 20* — et le règle
pour vous. Au-delà du nombre de versions, ça repart simplement du début.

Les deux modes se combinent : le tirage se fait après le découpage, donc chaque
bloc a le sien.

**Les stems**, via [Demucs](https://github.com/adefossez/demucs), en option,
dans son propre environnement pour ne pas perturber le PyTorch d'ACE-Step.

**Des copies MP3 et FLAC** à côté du WAV, via ffmpeg, également en option.

**Un dossier par morceau**, contenant l'audio, les formats en plus, les stems
et le `.txt`. Un lot nommé, c'est un lot qu'on retrouve trois jours plus tard.

---

## ⚠️ Trois choses à savoir avant le premier rendu

**1. En mode « As typed » avec tout sur Auto, aucune métadonnée n'atteint le
modèle.** Le tempo et la tonalité ne sont calculés que dans le chemin de
réécriture. Si vous coupez la réécriture et laissez BPM, tonalité et métrique
sur Auto, le modèle improvise toutes les décisions de structure — et c'est
précisément ce qui donne les résultats chaotiques dont tout le monde se plaint.
L'app affiche un bandeau d'avertissement quand les trois sont sur Auto. Le
remède : les régler vous-même.

**2. Écrire « instrumental » dans les paroles n'arrête pas le chant.** La case
**Instrumental** si, en ajoutant un refus explicite en tête de la description.
Elle est cochée par défaut.

**3. La description est plafonnée à 512 caractères.** Au-delà, le modèle coupe.

---

## 🍏 Ce qu'il faut

| | |
|---|---|
| **Mac** | Apple Silicon — M1 ou plus récent. Les Mac Intel ne peuvent pas. |
| **Mémoire** | 16 Go suffisent (avec le modèle de langage 0.6B). 24 Go et plus, c'est confortable. |
| **Disque** | ~25 Go, dont 10 à 16 Go de poids téléchargés au premier rendu. |
| **macOS** | Sonoma (14) ou plus récent. |
| **En plus** | ACE-Step 1.5 lui-même — voir [INSTALL.md](INSTALL.md). |
| **Optionnel** | ffmpeg (MP3/FLAC), Demucs (stems). |

---

## ⏱️ Mesuré sur un M4 Pro (64 Go)

De vrais chiffres, pas des estimations. Votre Mac sera différent, mais la forme
reste : **chaque rendu paie un coût fixe avant la moindre seconde d'audio**,
donc un morceau court ne coûte pas proportionnellement moins cher.

| Quoi | Réglages | Résultat |
|---|---|---|
| Un morceau de 120 s | Turbo, 8 étapes, batch 1 | environ 50 s |
| 80 fichiers | Turbo, 30 s chacun, batch 4 | environ 40 min |
| Même seed à 8 / 16 / 24 étapes | Turbo | **fichiers identiques à l'octet**, 43 / 47 / 56 s |
| MLX contre PyTorch-MPS | mêmes seed et réglages | 97 discontinuités contre **3062** |

La troisième ligne explique pourquoi le curseur Steps est désactivé sur Turbo :
les passes supplémentaires sont calculées puis jetées. La quatrième explique
pourquoi MLX est le défaut.


---

## 🎚️ Les réglages, dans l'ordre

### Description (Caption)

La description du morceau, pas les paroles. 512 caractères maximum.

**Caption handling**, juste en dessous :

- **As typed** — vos mots partent intacts.
- **Rewritten** — le modèle de langage les développe d'abord, en y ajoutant
  tempo, tonalité et métrique de son cru.
- **Both** — deux rendus sur le même seed, un de chaque. C'est la façon de
  comparer.

### Paroles

**Instrumental — no voice at all** est coché par défaut. Décoché, la case des
paroles s'ouvre, avec le choix de la langue chantée.

### Durée, tempo, tonalité, métrique

Durée en secondes ; 0 laisse le modèle décider. Le tempo a deux cases — une
valeur, et une borne haute si vous voulez une fourchette tirée par morceau ;
deuxième case à 0 pour un tempo fixe. Voir l'avertissement 1 plus haut au sujet
de la tonalité et de la métrique laissées sur Auto.

### Modèles

**Audio model.** *Turbo* est le rapide, et c'est par là qu'on commence. *SFT*
finit mieux et prend quatre à huit fois plus de temps. *Base* est le seul qui
accepte un CFG.

**Language model.** *1.7B* est le bon défaut. *0.6B* si la mémoire est serrée.
*4B* est connu pour saturer la mémoire sur macOS.

**Run the audio model on MLX as well** — à laisser coché. C'est le chemin
propre : mesuré sur le même seed, MLX produit 97 discontinuités de forme d'onde
là où PyTorch-MPS en produit 3062. À décocher seulement si un rendu échoue
bizarrement.

### Seed

`-1` = aléatoire. Un seed fixe rejoue le même morceau. **Add 1 to the seed for
each extra track** explore autour d'une idée qui marche — même famille,
vraies variations.

### Lots

**Number of tracks**, jusqu'à 100. **Batch size** en rend plusieurs à la fois en
partageant la partie coûteuse. **Batch name** nomme le dossier — prenez
l'habitude, un lot sans nom est un lot perdu.

---

## 🔧 Notes de conception

Quelques décisions volontaires, au cas où elles ressembleraient à des oublis :

- **L'app importe les handlers d'ACE-Step** et appelle leur propre
  `generate_music` au lieu de réimplémenter quoi que ce soit : elle reste juste
  quand leur projet bouge. C'est aussi pour ça qu'elle doit tourner dans leur
  environnement virtuel.
- **Elle filtre les réglages qu'elle envoie.** Si ACE-Step renomme un champ,
  vous perdez ce réglage-là et le journal vous dit lequel, au lieu de planter.
- **Demucs est volontairement dans un environnement séparé.** Il lui faut un
  autre PyTorch. L'installer à côté casserait ACE-Step.
- **Rien n'est jamais envoyé nulle part.** Pas de télémétrie, pas de compte,
  aucun appel réseau sauf celui qui télécharge les poids du modèle.

---

## 📜 Licences et attribution

**Cette interface** est en MIT — voir [LICENSE](LICENSE). Faites-en ce que vous
voulez.

**ACE-Step 1.5 n'est pas inclus ici** et n'est pas couvert par cette licence.
C'est vous qui le téléchargez, depuis son propre projet, sous ses propres
termes. À l'heure où j'écris, ce projet est en **MIT**, ce qui — contrairement
à plusieurs autres modèles de musique — ne vous impose aucune restriction non
commerciale. Mais les licences changent : allez voir
[la leur](https://github.com/ace-step/ACE-Step-1.5/blob/main/LICENSE) plutôt
que de me croire sur parole, surtout avant de vendre quoi que ce soit.

**Les poids du modèle** sont téléchargés depuis le projet ACE-Step au premier
rendu et restent sur votre machine.

**Demucs**, qui fait la séparation en stems en option, est un projet séparé
avec sa propre licence : [adefossez/demucs](https://github.com/adefossez/demucs).

Rien dans ce dépôt n'est de l'audio généré, et aucun son que vous faites avec
ne passe par moi ni par personne.

---

## 👋 Qui a fait ça

Jean-Pascal — **[Quick-Eyed Sky](https://www.youtube.com/@QuickEyedSky)** sur
YouTube, [QES](https://huggingface.co/QES) sur Hugging Face. Pas programmeur :
ceci existe parce que les réglages n'étaient expliqués nulle part et que je
voulais les comprendre.

Si ça vous a épargné un après-midi, vous pouvez
[m'offrir un café](https://buymeacoffee.com/oFJ5CiY7n). Entièrement facultatif,
et le projet reste exactement aussi gratuit dans les deux cas.

---

## 🙏 Merci

À [l'équipe ACE-Step](https://github.com/ace-step/ACE-Step-1.5) pour le modèle
et pour avoir pris Apple Silicon au sérieux, et à
[Demucs](https://github.com/adefossez/demucs) pour la séparation des pistes.
