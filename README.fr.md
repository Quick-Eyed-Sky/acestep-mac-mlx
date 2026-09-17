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

## Pourquoi cette interface

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

## Ce qu'elle fait

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

**Prompts dynamiques et séquentiels**, détectés automatiquement :

```
a {slow|fast} {piano|guitar} piece, {warm|cold}
```

tire une option de chaque à chaque rendu, tandis que les blocs séparés par une
ligne de **trois tirets ou plus** passent chacun leur tour :

```
première idée
---
deuxième idée
```

Les deux se combinent : le tirage se fait après le découpage, donc chaque bloc
a le sien.

**Les stems**, via [Demucs](https://github.com/adefossez/demucs), en option,
dans son propre environnement pour ne pas perturber le PyTorch d'ACE-Step.

**Des copies MP3 et FLAC** à côté du WAV, via ffmpeg, également en option.

**Un dossier par morceau**, contenant l'audio, les formats en plus, les stems
et le `.txt`. Un lot nommé, c'est un lot qu'on retrouve trois jours plus tard.

---

## Trois choses à savoir avant le premier rendu

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

## TEXTURES.txt

Inclus dans ce dépôt : **62 descriptions de textures sonores**, séparées par
`---` et prêtes à coller telles quelles dans la case description, en mode
séquentiel. Vent, arbres, pluie, orage, feu, pas, canon, métal, pleurs,
bâtiments vides, et une série de choses parfaitement non identifiables.

Ce ne sont pas vraiment des bruitages. C'est un modèle de musique : quand on
lui demande un canon, il répond par une **texture**. C'est tout l'intérêt — une
minute de chacune fait des fonds remarquables.

Utilisation : ouvrir le fichier, tout copier, coller dans la description,
durée 60, 62 morceaux, nommer le lot, Generate.

---

## Ce qu'il faut

| | |
|---|---|
| **Mac** | Apple Silicon — M1 ou plus récent. Les Mac Intel ne peuvent pas. |
| **Mémoire** | 16 Go suffisent (avec le modèle de langage 0.6B). 24 Go et plus, c'est confortable. |
| **Disque** | ~25 Go, dont 10 à 16 Go de poids téléchargés au premier rendu. |
| **macOS** | Sonoma (14) ou plus récent. |
| **En plus** | ACE-Step 1.5 lui-même — voir [INSTALL.md](INSTALL.md). |
| **Optionnel** | ffmpeg (MP3/FLAC), Demucs (stems). |

---

## Mesuré sur un M4 Pro (64 Go)

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

## Les réglages, dans l'ordre

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

**Number of tracks**, jusqu'à 50. **Batch size** en rend plusieurs à la fois en
partageant la partie coûteuse. **Batch name** nomme le dossier — prenez
l'habitude, un lot sans nom est un lot perdu.

---

## Notes de conception

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

## Licences et attribution

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

## Qui a fait ça

Jean-Pascal — **[Quick-Eyed Sky](https://www.youtube.com/@QuickEyedSky)** sur
YouTube, [QES](https://huggingface.co/QES) sur Hugging Face. Pas programmeur :
ceci existe parce que les réglages n'étaient expliqués nulle part et que je
voulais les comprendre.

Si ça vous a épargné un après-midi, vous pouvez
[m'offrir un café](https://buymeacoffee.com/oFJ5CiY7n). Entièrement facultatif,
et le projet reste exactement aussi gratuit dans les deux cas.

---

## Merci

À [l'équipe ACE-Step](https://github.com/ace-step/ACE-Step-1.5) pour le modèle
et pour avoir pris Apple Silicon au sérieux, et à
[Demucs](https://github.com/adefossez/demucs) pour la séparation des pistes.
