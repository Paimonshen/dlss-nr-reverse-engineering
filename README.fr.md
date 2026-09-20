# Rétro-ingénierie de DLSS NR : module AMD → récupération des sources multi-GPU

> **En une ligne** : une étude complète de rétro-ingénierie statique du module DLSS NR côté AMD — la base pour **récupérer un arbre de sources reconstruisible** puis, à partir de lui, une **base de code unique multi-GPU** dotée de backends portable, accéléré par Intel, accéléré par AMD et de référence NVIDIA. L'étude est achevée et dit honnêtement où elle s'est bloquée ; **le travail de récupération est l'étape suivante**.

**Languages / 语言 / 言語 / 언어 / Idioma / Langue:**
[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [**Français**](README.fr.md)

> Les traductions sont maintenues par la communauté. Si une traduction prend du retard, **l'anglais fait foi**. Les corrections sont bienvenues — voir [CONTRIBUTING.md](CONTRIBUTING.md).

---

## En un coup d'œil

| | |
|---|---|
| **Objet** | `dlssnr_amd_pass1.dll` —— un module proxy `version.dll` côté AMD contenant du code de périphérique HIP `amdgcn`. 7 156 224 B, SHA256 `3C9CA13F…2BC1DD8`. Les trois fichiers `pass1/2/3` sont **identiques octet pour octet** (réalité du paquet de publication, pas trois étapes). |
| **Ce qui est fait** | Analyse statique complète : **12 sections**, **17 exports**, **194 importations / 10 DLL**, **8 cibles de périphérique × 34 noyaux (272 entrées)**, la spécification complète des paramètres de noyau, le **conteneur de poids décodé** (153 entrées + 147 683 778 B de charge utile) et l'appariement **34/34** des enregistrements de noyau (clos par preuve directe en octets). |
| **Cible du portage** | **Tous les GPU Intel dotés de moteurs XMX** —— Xe-HPG (**série Arc A**) et Xe2 (**série Arc B**) et suivants. **Intel Arc B580 est la machine de développement et de vérification**, et non la seule cible. |
| **Niveau de preuve** | **Niveau d'octet statique.** Pas de matériel AMD ⇒ pas d'observation à l'exécution ; pas de désassembleur AMDGPU ; pas de chaîne d'outils Intel. Chaque affirmation porte un fichier/RVA/octets ou une citation. |
| **État** | Analyse **terminée** ; **la récupération des sources est l'étape suivante** (voir les [objectifs du projet](#où-cela-mène-objectifs-du-projet)). **Trois manques restent ouverts** —— voir [Aide recherchée](#aide-recherchée-trois-manques-précis-que-nous-navons-pas-pu-combler). |
| **Porte de qualité** | CI à chaque push : audit des ancres/liens/motifs, gardes sur les binaires NVIDIA et les chemins absolus, test de fumée des outils, et **vérification des hachages publiés**. |
| **Commencez ici** | [docs/README.md](docs/README.md) —— l'index des documents. Les documents d'analyse sont en **anglais et en chinois** ; la méthodologie est en chinois. |

---

## 🎯 Où cela mène (objectifs du projet)

Ce dépôt a commencé comme une analyse statique — mais l'analyse n'a jamais été qu'**un moyen au service d'une fin**. L'objectif que nous poursuivons désormais, dans l'ordre :

### Stage 1 — Récupérer les sources : décompiler le programme principal

Passer de *comprendre des octets* à **un arbre de sources maintenable** : décompiler le programme principal et récupérer des sources lisibles et reconstruisibles. La spécification des paramètres de kernel ([`docs/04`](docs/04-Kernel-Parameter-Spec.md)), le format du conteneur de poids et le mécanisme d'enregistrement constituent le **matériel de référence** qui rend une reconstruction fidèle vérifiable — c'est pourquoi ils ont été produits en premier.

> ⚠️ **Blocage connu, dit d'emblée.** Récupérer un arbre de sources *utilisable* exige la **liaison de distribution `71 block → kernel`** ; sans elle, la couche d'ordonnancement reconstruite reste une coquille trouée en son milieu. Cette liaison est actuellement **impossible à obtenir dans les conditions disponibles** (les quatre pistes sont fermées — voir [Aide recherchée](#aide-recherchée-trois-manques-précis-que-nous-navons-pas-pu-combler) et [`docs/06`](docs/06-Open-Gaps-and-Limits.md)). L'effort de décompilation **butera donc sur le même manque**. Le travail vaut malgré tout la peine — l'essentiel de l'arbre peut être récupéré —, mais la couche de distribution ne peut pas être close par la seule décompilation.

### Stage 2 — Une compilation en instructions communes qui tourne partout

Avant d'optimiser, la faire **tourner tout court**. Produire une compilation qui **n'utilise aucun jeu d'instructions propriétaire d'un fabricant** : un chemin de calcul simple et portable. Cela établit l'exactitude et donne à chaque backend ultérieur une **référence valide et connue à laquelle se comparer**.

### Stage 3 — Des compilations accélérées par fabricant

Une fois la compilation portable fonctionnelle, ajouter l'**accélération propre à chaque fabricant** sous forme de backends distincts :

| Backend | Cible | Chemin d'accélération |
|---|---|---|
| **Accélération Intel** | Intel Arc (Xe) | Xe Matrix Extensions (XMX) |
| **Accélération AMD** | AMD RDNA / CDNA | HIP et cœurs matriciels |
| **Original NVIDIA** | NVIDIA | l'implémentation NGX / DLSS du fabricant lui-même |

> ⚠️ **Contrainte propre au chemin NVIDIA.** Ce dépôt **ne contient pas de binaires sous copyright NVIDIA** ([`LEGAL.md`](LEGAL.md) §8), et il a été confirmé que la copie publiquement disponible du composant NVIDIA est une **couche d'interface ne portant aucune métadonnée de kernel analysable** (voir [`EXTERNAL_BINARIES.md`](EXTERNAL_BINARIES.md) et [`docs/03`](docs/03-DLL-Structure-Analysis.md)). Le chemin NVIDIA est donc utilisable **comme référence pour le comportement de l'interface et pour recouper les résultats** — il **n'est pas** une source de kernels décompilables. Tout travail côté NVIDIA ici reste au niveau de l'interface / de la documentation.

### Stage 4 — Une seule base de code, tous les GPU

**Intégrer les backends dans un arbre de sources unique** avec un mécanisme de sélection de backend, afin qu'**une seule base de code cible tous les GPU pris en charge** : le chemin portable comme repli universel, l'accélération par fabricant là où elle est disponible.

> **En une phrase :** *récupérer les sources → les faire tourner de façon portable → les accélérer par fabricant → les unifier en une seule base de code multi-GPU.*

> **État de ces étapes.** Les étapes 2 à 4 décrivent l'**orientation visée, et non un travail achevé**. Ce dépôt ne contient actuellement que de l'**analyse et des outils** — aucun arbre de sources décompilé et aucune implémentation de backend. Tout ce qui est publié ici se situe au **niveau statique des octets**. Nous préférons le dire clairement plutôt que de suggérer des progrès que nous ne pouvons pas étayer.

## 🙏 Aide recherchée : trois manques précis que nous n'avons pas pu combler

Ce **n'est pas une étude « terminée »**. Nous avons déterminé tout ce qui peut l'être statiquement — **les 34 noms de kernels, la disposition des paramètres de kernels, le format du conteneur de poids et la surface d'import de 194 entrées sont clos** —, mais **trois manques** restent impossibles à combler dans les conditions dont disposait l'auteur d'origine. Nous demandons de l'aide explicitement.

### Manque 1 : la liaison `71 block → kernel` (**le plus critique**)

**Ce dont nous avons besoin** : quelle couche (`blockN.layerM`) distribue vers lequel des 34 kernels.

**Pourquoi nous ne pouvons pas l'obtenir** (les quatre pistes sont fermées, chacune avec preuve) :
1. **L'analyse statique de la DLL est à sa limite** — le corps de la fonction de distribution n'a aucune intersection avec les fonctions de lancement de kernels.
2. **Le code source de l'espace de travail est une coquille vide** — un projet de réimplémentation existe, mais les corps de ses fonctions de distribution ne contiennent que `return true;`, et il **n'est pas isomorphe** à cette DLL (seuls 2 des 34 noms de kernels coïncident).
3. **Le fichier de poids est épuisé** — nous avons cherché avec **140 motifs d'octets** sur **tout le fichier, charge utile comprise** : `shape` / `dtype` / type d'opérateur / index de `block` / nom de `kernel` ont tous renvoyé **0 correspondance**, et la comptabilité octet par octet de la région d'index montre **des octets non attribués = 0** (pas de seconde table, pas de région de métadonnées cachée).
4. **L'observation à l'exécution est indisponible** — nous n'avons pas de matériel AMD.

**Si vous pouvez fournir** : ① la définition du réseau amont (`.onnx` / `.safetensors` / script d'export) ; ② le code source du côté pass amont ; ③ ou un vidage de la séquence de distribution réelle issue d'une exécution sur matériel AMD — veuillez ouvrir une Issue. **Cela détermine directement si la feuille de route de portage peut aboutir.**

### Manque 2 : la disposition interne des champs de deux structures de paramètres

**`VarParams` (168 octets, la structure de paramètres utilisateur des 5 kernels `k_swin_var`)** et **`SwinParams` (40 octets, `k_swin_1h_32_fp8`)** ont une composition interne de champs non résolue.

**Ce que nous savons** : les métadonnées de la DLL ne déclarent que le **nombre total d'octets** du paramètre `by_value` (168 / 40) ; elles ne comportent **ni noms de champs ni frontières de champs**. Nous avons lu des structures de même nom dans un arbre de code source de réimplémentation (92 octets en supposant des pointeurs 64 bits), mais celles-ci **ne correspondent ni à 168 ni à 40** — les structures du code source **ne peuvent donc pas** servir de disposition côté DLL.

**Si vous pouvez fournir** : les définitions de structures du code source amont, ou les règles de disposition des structures `by_value` de la chaîne d'outils AMD (y compris le remplissage implicite) — veuillez ouvrir une Issue.

### Manque 3 : confirmer les capacités d'Intel Xe / XMX (une **liste de 51 points**)

Nous avons construit une table de correspondance 34 kernels × opérateurs, mais **les colonnes « prise en charge directe par XMX » et « chemin recommandé » de la table sont marquées « documentation externe requise » pour les 34/34 lignes — nous n'avons délibérément émis aucune conclusion sur les capacités**, faute de chaîne d'outils Intel et de matériel Xe pour le vérifier.

**Si vous connaissez Intel Arc / oneAPI / Level Zero / SPIR-V**, aidez-nous à confirmer les points précis (priorité absolue : la prise en charge des primitives XMX et les modes de précision pour la multiplication matricielle/convolution ; savoir si l'ordre de réduction du split-K est contraint par la spécification ; les primitives de fenêtre/décalage de Swin ; et la frontière de faisabilité du chemin SPIR-V générique). La liste se trouve dans [docs/05-Intel可行性评估.md](docs/05-Intel可行性评估.md), chapitre 8.

> **Méthodologie du projet** : tout ce dont nous ne sommes pas certains est marqué « documentation externe requise » et **nous ne spéculons jamais**. Ces blancs dans la table sont **délibérés, et non des omissions**.

---

## Ce que ce projet a fait

Une analyse statique complète de `dlssnr_amd_pass1.dll` côté AMD (un module proxy `version.dll` contenant du code de périphérique HIP `amdgcn`), pour répondre à :

> **DLSS NR peut-il être recompilé/porté de AMD HIP vers les GPU Intel dotés de moteurs XMX (Xe-HPG / Xe2 et suivants) ?**

La cible est **la famille Intel équipée de XMX**, et non une carte unique. **Intel Arc B580 (Xe2 / Battlemage) est la machine de développement et de vérification** — la seule pièce disponible ici, donc la seule contre laquelle on peut réellement compiler et tester. Lorsqu'une capacité varie selon la génération, **la base portable est l'ensemble pris en charge par toutes les générations cibles** ; tout ce qui va au-delà est un **chemin optionnel derrière une détection à l'exécution**. Voir [`docs/07`](docs/07-External-Evidence-Xe-Capabilities.md) pour les données générationnelles sourcées.

### Résultats principaux (tous reproductibles)

| Résultat | Contenu | Doc |
|---|---|---|
| **Forme du module** | 12 sections ; 17 exports, **tous des noms d'API `version.dll`** (chacun un stub de saut `FF 25` de 16 octets) ; surface d'import de **194 entrées / 10 DLL**, dont `amdhip64_7.dll` apporte **29** API HIP | `docs/03` |
| **Code de périphérique** | `.hip_fat` est un clang offload bundle : **9 bundles = 1 espace réservé hôte + 8 cibles de périphérique**, toutes `amdgcn-amd-amdhsa` ; **34 kernels** par cible | `docs/03` |
| **Spécification des paramètres de kernel** | Pour les 34 kernels : `kernarg_segment_size`, tailles `by_value`, tables `.args` complètes, champs de ressources ; **3 kernels d'exception** (`k_flag_wait`=16 / `k_align_probe`=8 / `k_flag_set`=12) | `docs/04` |
| **Appariement d'enregistrement 34/34** | Deux tables de pointeurs de fonction à **pas de 8 octets** + **34 appels d'enregistrement appariés aux emplacements de table 34/34** ⇒ « nom de kernel ↔ enveloppe ↔ emplacement » clos statiquement | `docs/03` |
| **Conteneur de poids décodé** | `8B magic "DLSSNRW1"` + nombre d'entrées `uint32` (153) + décalage de fin d'index `uint32` (0x1629) + 153 descripteurs de longueur variable + charge utile contiguë (147,683,778 B) ; **trois identités se closent à 0** | `docs/05` |
| **Faisabilité Intel** | Classes de kernels **A=7 / B=20 / C=7** ; adaptation des ressources (`group_segment_fixed_size` maximal **64,640 B**, **896 B** sous la limite de 64 Kio) ; côté hôte, **29/194 = 14.9%** à remplacer ; **feuille de route S0–S7 avec 23 jalons** | `docs/05` |
| **Outils d'analyse** | Trois outils génériques en lecture seule : analyseur PE, extracteur de métadonnées msgpack AMDGPU, scanner d'octets | `tools/` |
| **Méthodologie de collaboration** | Flux de travail multi-agents, portes qualité et chaîne d'acceptation, **24 règles issues d'incidents réels** | `team-methodology/` |

### Conclusions fermes (y compris nos propres corrections)

Nous **avons conservé la trace des corrections**, y compris les revirements de nos propres conclusions antérieures :

- ✅ **L'appariement d'enregistrement 34/34 est une preuve directe par les octets** (il avait un temps été rédigé comme « inférence par élimination »).
- ✅ **Les mesures de poids renversent les constantes du code source** : la structure réelle des couches est **1×47 / 4×15 (23–29, 40–47) / 5×9 (30–38)**, en contradiction avec le « goulot uniformément de 4 couches » du code source (**blocs incohérents : 10 = 30–39**) ; en cas de conflit, **le fichier de données l'emporte**.
- ✅ **Le delta de `descsz` a été corrigé de 1,410 à 938** (une erreur arithmétique), et il y a **6 valeurs distinctes** après déduplication.
- ✅ **La contrainte « pas de code source amont » a été renversée** : l'espace de travail **contient bien** un arbre de code source côté pass (mais non isomorphe à la DLL) ; le « il n'existe pas » antérieur était un **faux négatif** dû à un périmètre de recherche trop étroit.
- ✅ **La borne supérieure de l'énumération `71 block` reste indéterminée** : ce nombre n'apparaît que dans des transcriptions de documentation ; il n'y a pas d'immédiat correspondant dans la DLL.

> Une règle ferme de notre méthodologie : **toute affirmation « X n'existe pas » doit donner plage + motif + nombre de correspondances.** C'est pourquoi vous verrez de nombreux relevés reproductibles de « 0 correspondance » dans la documentation — c'est délibéré.

---

## Arborescence du dépôt

```
.
├── README.md                  Ce fichier (anglais, fait foi)
├── README.zh-CN.md            简体中文
├── README.ja.md               日本語
├── README.ko.md               한국어
├── README.es.md               Español
├── README.fr.md               Français
├── LEGAL.md                   Mention légale (nature du projet, droits, retrait)
├── EXTERNAL_BINARIES.md       Binaires tiers (origine / taille / SHA256 / licence / usage)
├── LICENSE                    MIT (œuvre originale) + exclusion explicite des binaires tiers
├── CONTRIBUTING.md            Guide de contribution (exigences de preuve)
├── .gitattributes             Configuration Git LFS
├── .gitignore
├── docs/
│   ├── 01-项目背景.md            Objectif du projet, cible d'analyse, trois contraintes d'environnement
│   ├── 02-分析方法论.md          Chaîne de méthodes et discipline d'analyse
│   ├── 03-DLL结构分析.md         Forme du module, code de périphérique, les deux tables de pointeurs, enregistrement
│   ├── 04-内核参数规格.md        Tables complètes des paramètres et ressources des 34 kernels
│   ├── 05-Intel可行性评估.md     Classification / ressources / opérateurs / remplacement côté hôte / poids / feuille de route / liste de vérification
│   └── 06-未解缺口与限制.md      Limites honnêtes : ce que nous n'avons pas pu produire, et pourquoi
├── tools/
│   ├── pe_parser.py         Analyse PE32/PE32+ (traitement manuel de .reloc, .pdata)
│   ├── msgpack_extract.py   Extraction des métadonnées de kernel AMDGPU
│   ├── byte_scanner.py      Analyse générique de motifs d'octets / histogramme / entropie / chaînes
│   └── README.md
├── team-methodology/
│   ├── 01-多智能体协作流程.md
│   ├── 02-质量门禁与验收链.md
│   ├── 03-已确立的定规.md     24 règles, chacune issue d'une erreur réelle
│   └── 04-禁用措辞检查的校准.md
└── binaries/                 Binaires tiers (Git LFS)
    ├── dlssnr_amd_pass1.dll
    ├── dlssnr_amd_pass2.dll
    ├── dlssnr_amd_pass3.dll
    ├── dlssnr_on_amd_weights.bin
    └── OptiScaler/
        └── OptiScaler.dll
```

> Remarque : les trois DLL `pass1/2/3` sont **identiques octet pour octet** (même SHA256). C'est la structure réelle du paquet de distribution, et non trois étapes de traitement.

> **Remarque sur la langue de la documentation** : les six documents d'analyse de `docs/` et les quatre documents de méthodologie de `team-methodology/` sont actuellement rédigés en **chinois**. Les traductions anglaises sont bienvenues — voir [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Démarrage rapide

```bash
git clone https://github.com/Paimonshen/dlss-nr-reverse-engineering.git
cd dlss-nr-reverse-engineering

# Binaries are tracked by Git LFS; pull real content after cloning (~186 MB)
git lfs install
git lfs pull
```

### Dépendances

```bash
pip install pefile msgpack    # Python 3.11+
```

### Reproduire les résultats principaux

```bash
# 1) Module shape: 12 sections / 17 version.dll exports / 194 imports (10 DLLs)
python tools/pe_parser.py info binaries/dlssnr_amd_pass1.dll --limit 0

# 2) Relocations: 19 blocks, 2044 entries (DIR64 2040 + ABSOLUTE 4)
python tools/pe_parser.py reloc binaries/dlssnr_amd_pass1.dll

# 3) Exception table: 1167 entries
python tools/pe_parser.py pdata binaries/dlssnr_amd_pass1.dll --pdata-limit 0

# 4) 8 device targets x 34 kernels, with kernarg size and by_value args
python tools/msgpack_extract.py binaries/dlssnr_amd_pass1.dll --json out/kernels.json

# 5) Weight container magic (1 hit) and payload byte distribution (entropy 5.902444 bits/byte)
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --hex "44 4C 53 53 4E 52 57 31"
python tools/byte_scanner.py binaries/dlssnr_on_amd_weights.bin --byte-histogram --range 0x1629:
```

Les trois outils sont en **lecture seule** (ils n'écrivent rien, sauf vers des chemins explicites `--out` / `--json` / `--hex-out`). Voir [tools/README.md](tools/README.md).

---

## Trois contraintes d'environnement (à noter)

Chaque conclusion est bornée par ces trois contraintes, et la documentation les signale tout au long du texte :

1. **Pas de matériel AMD** ⇒ pas d'observation à l'exécution (la plus critique des trois lacunes).
2. **Pas de désassembleur AMDGPU** (`llvm-objdump` indisponible) ⇒ pas de désassemblage côté périphérique ; les relations d'appel de symboles tels que `swin_layer` ne sont pas démontrées.
3. **Pas de chaîne d'outils Intel / matériel Xe** ⇒ tout ce qui concerne des capacités précises de Xe / SPIR-V / XMX est **marqué « documentation externe requise » et laissé sans conclusion**.

**Par conséquent, le niveau de nos conclusions est « niveau octet statique »** : ce qui peut être donné l'est avec preuves à l'appui au niveau des octets ; ce qui ne peut pas l'être est marqué « non résolu » avec une demande de documentation externe.

---

## Comment contribuer

- **Combler les trois manques** (voir « Aide recherchée » ci-dessus) — la contribution la plus précieuse.
- **Corriger une conclusion** : si une conclusion documentée contredit les preuves au niveau des octets, veuillez joindre **fichier + décalage + octets bruts + commande de reproduction**.
- **Fournir de la documentation externe** pour les points marqués « documentation externe requise ».
- **Améliorer les outils ou la documentation.**

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Ce projet a des exigences de preuve élevées (les négations universelles doivent donner plage + motif + nombre de correspondances), mais **une PR avec une conclusion correcte et des preuves insuffisantes se verra seulement demander d'ajouter des preuves, jamais rejetée d'emblée**.

## Licence et aspects juridiques

- L'**œuvre originale** (documentation, scripts) est sous **licence MIT** — voir [LICENSE](LICENSE).
- Les **binaires tiers** (sous `binaries/`) ne sont **pas** couverts par cette licence ; les droits d'auteur appartiennent à leurs détenteurs respectifs. Les origines et les SHA256 figurent dans [EXTERNAL_BINARIES.md](EXTERNAL_BINARIES.md).
- Il s'agit de **recherche d'interopérabilité**. Elle ne contient aucun code de contournement de DRM ni aucun binaire protégé par le droit d'auteur de NVIDIA. Si un détenteur de droits demande le retrait, nous nous y conformerons immédiatement — voir [LEGAL.md](LEGAL.md).

## Avertissement

Il s'agit d'une recherche statique indépendante, fournie **« en l'état », sans garantie d'aucune sorte**. Les utilisateurs **assument tous les risques et toute la responsabilité juridique** liés à tout usage du contenu de ce dépôt.
