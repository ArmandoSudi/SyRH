# Questions ouvertes — SIRH ARPTC

État au 17 novembre 2026. Ces questions n'ont pas encore de réponse ; elles complètent le
[cahier des charges](cahier-des-charges-sirh-arptc.md) (section 13). Cocher une question et noter la
réponse sous elle quand elle est tranchée, puis reporter la règle dans le cahier des charges.

En attendant, le MVP traite chaque point comme un **paramètre** ou applique l'hypothèse indiquée.

## 1. Dépendants

- [ ] **Q1 — Enfants à charge au-delà de 25 ans.** Le droit est-il prolongé pour études ?
  - Concerne : ADM-15, ADM-16.
  - Hypothèse MVP : aucune prolongation, fin du droit à 25 ans.

## 2. Carrière et sortie

- [ ] **Q2 — Autres motifs de sortie définitive.** Faut-il prévoir licenciement, fin de contrat,
  révocation, inaptitude ?
  - Concerne : section 2.2, CAR-16.
  - Hypothèse MVP : référentiel des motifs paramétrable, avec décès, démission et retraite au départ.
    Appliquée par la roadmap 1.6 (motifs de sortie).
- [ ] **Q3 — Mise en disponibilité et 30 ans de carrière.** La période de mise en disponibilité
  compte-t-elle dans les 30 ans, comme celle de détachement ?
  - Concerne : section 2.3, CAR-14, SOC-07.
  - Hypothèse MVP : indicateur « compte dans l'ancienneté » par type de suspension. Appliquée par
    la roadmap 1.6 : la mise en disponibilité ne compte pas dans les données de démonstration.
- [ ] **Q4 — Portée de « l'agent ne bénéficie de rien ».** La règle s'applique-t-elle à la mise en
  disponibilité comme au détachement ? Suspend-elle aussi les bons de soins des dépendants ?
  - Concerne : section 2.3, CAR-08.
  - Hypothèse MVP : paie, allocations familiales et bons de soins suspendus dans les deux cas,
    dépendants compris.
- [ ] **Q5 — Format du matricule.** Faut-il le générer automatiquement sous la forme
  préfixe / numéro d'ordre / année d'engagement, comme sur le bulletin fourni ?
  - Concerne : SOC-01.

## 3. Rémunération

- [ ] **Q6 — Prime d'ancienneté et prime d'annuité.** S'agit-il de la même prime ? Selon quel barème
  évolue-t-elle ?
  - Concerne : CAR-10, REM-26.
- [ ] **Q7 — Composantes liées au grade.** Lesquelles dépendent du grade : salaire de base, logement,
  transport, autres ?
  - Concerne : REM-24.
- [ ] **Q8 — Transport pendant la maladie et la maternité.** Est-il retenu au prorata des jours
  d'absence ? Le reste du salaire est-il maintenu en totalité, sans limite de durée ?
  - Concerne : ADM-05, ADM-06, REM-27.
  - Hypothèse MVP : retenue au prorata des jours, reste du salaire maintenu.
- [ ] **Q9 — CNSS avec affiliation « en cours ».** La quote-part ouvrière est-elle nulle tant que
  l'affiliation n'est pas faite, puis régularisée ?
  - Concerne : REM-03, section 7.6.
- [ ] **Q10 — Liste complète des gains et retenues.** Quelles autres rubriques peuvent figurer sur un
  bulletin : intérim, heures supplémentaires, allocations familiales, prêts, avances ?
  - Concerne : REM-01, REM-30.
- [ ] **Q11 — Valeurs des barèmes.** Grille salariale, prime d'intérim, majorations des heures
  supplémentaires, allocations familiales, cotisation syndicale, taux de CNSS et barème de l'IPR.
  - Concerne : REM-23. Ce sont des paramètres à renseigner dans le système, non à coder.

## 4. Social

- [ ] **Q12 — Plafonds de prise en charge médicale.** Existe-t-il des plafonds, et une quote-part à
  charge de l'agent ?
  - Concerne : SOC-M-05, SOC-M-18.
- [ ] **Q13 — Hôpitaux et prestataires conventionnés.** Combien sont-ils, et dans quel format
  transmettent-ils la facture et la grille tarifaire ?
  - Concerne : SOC-M-07, SOC-M-09, SOC-M-11.

## 5. Technique et organisation

- [ ] **Q14 — Logiciels existants à interfacer.** Y a-t-il un logiciel de paie et un logiciel
  comptable en place ? Quel mode de liaison avec la pointeuse : interface directe ou import de fichier ?
  - Concerne : ADM-01, REM-22, TEC-04, REP-01.
- [ ] **Q15 — Effectif chiffré.** Nombre d'agents, de stagiaires, de journaliers et d'utilisateurs du
  SIRH.
  - Concerne : NF-08, NF-09.
- [ ] **Q16 — Modèle du fichier Excel de virement.** Quelles colonnes chaque banque attend-elle ?
  - Concerne : REM-20, REM-28.
- [ ] **Q27 — Organigramme de l'ARPTC.** Quelles sont les directions, départements, services et
  bureaux, avec leur sigle, et quels sont les sites (siège et représentations provinciales) ?
  Existe-t-il un niveau entre la direction et le département (division) ? La Direction générale
  est-elle au-dessus des directions, ou à leur niveau ?
  - Concerne : section 4.1 (structure organisationnelle), NF-11, roadmap 1.1.
  - Hypothèse en attendant : quatre niveaux ; la Direction générale et chaque représentation
    provinciale sont enregistrées comme des directions. Les RH saisissent la structure réelle
    dans l'administration.
- [ ] **Q28 — Grille de classification de l'ARPTC.** Quelles sont les catégories et les grades,
  avec leur sigle et leur ordre, et combien d'échelons compte chaque grade ? Un grade
  appartient-il toujours à une seule catégorie ? Les échelons sont-ils numérotés à partir de 1
  dans chaque grade ?
  - Concerne : section 4.1 (catégories, grades, échelons), CAR-06, REM-24, roadmap 1.2.
  - Hypothèse en attendant : trois niveaux imbriqués (catégorie, grade, échelon), chaque grade
    dans une seule catégorie, échelons numérotés par grade. Les RH saisissent la grille réelle
    dans l'administration.
- [ ] **Q29 — Liste des fonctions de l'ARPTC.** Quelles sont les fonctions, avec leur sigle et
  leur intitulé, et lesquelles sont des postes de responsabilité (direction d'une unité ou d'une
  équipe) ? Une fonction exige-t-elle une catégorie ou un grade minimum ?
  - Concerne : section 4.1 (fonctions), section 4.2 (position), CAR-08, CAR-09, roadmap 1.3.
  - Hypothèse en attendant : une liste plate, chaque fonction de nature « responsabilité » ou
    « exécution », sans lien avec la grille. Les RH saisissent la liste réelle dans
    l'administration.
- [ ] **Q30 — Types de contrat de l'ARPTC.** Existe-t-il d'autres types que CDI, CDD, stage et
  journalier (apprentissage, consultance, détachement entrant) ? Lesquels exigent une date de fin,
  et lesquels admettent une période d'essai ? Quelle est la durée de la période d'essai, dépend-elle
  du type de contrat ou de la catégorie, et un CDD peut-il être renouvelé, combien de fois ?
  - Concerne : section 4.1 (types de contrat), section 4.2 (contrat), CAR-03, CAR-04, roadmap 1.4.
  - Hypothèse en attendant : les quatre types de la section 4.1, chacun avec deux règles
    (« durée déterminée », « période d'essai ») ; la durée de l'essai et les renouvellements ne
    sont pas modélisés. Les RH saisissent la liste réelle dans l'administration.
- [ ] **Q31 — Pièces justificatives de l'ARPTC.** Quels types de pièces existent, et pour chaque
  événement (engagement, promotion, mutation, détachement, mise en disponibilité, reprise,
  intérim, sanction, distinction, sortie, mariage, naissance, fin de qualité de dépendant,
  formation), lesquelles sont obligatoires et lesquelles facultatives ? Une pièce exigée dépend-elle
  parfois de l'agent (catégorie, type de contrat, nationalité) ? L'Administration du personnel
  doit-elle modifier elle-même les pièces exigées pour les dépendants ?
  - Concerne : section 4.1 (types de pièces justificatives), SOC-04, CAR-02, ADM-14, roadmap 1.5.
  - Hypothèse en attendant : une pièce exigée ne dépend que de l'événement ; la Gestion de
    carrière et l'administrateur saisissent la liste réelle dans l'administration.
- [ ] **Q32 — Motifs de sortie et positions de suspension de l'ARPTC.** Quels motifs de sortie et
  quelles positions de suspension existent, avec quel sigle et quelle pièce exigée pour chacun ?
  Quelles sont la durée maximale et le nombre de renouvellements réels de chaque position ? Le
  préavis de démission a-t-il une durée fixe à paramétrer ?
  - Concerne : sections 2.2, 2.3 et 4.1 (motifs de sortie), CAR-08, CAR-16, roadmap 1.6.
  - Hypothèse en attendant : les quatre motifs de la section 2.2 et les deux positions de la
    section 2.3 ; pas de paramètre de préavis. La Gestion de carrière et l'administrateur
    saisissent la liste réelle dans l'administration.

## 6. Circuits de validation

À trancher avant la phase 2.11 de la feuille de route (circuit de validation). Le principe retenu :
chaque service saisit, son chef de service valide, et la Direction RH n'approuve que les décisions
qui engagent l'ARPTC (argent, droit, carrière) ; pour le reste, elle supervise l'avancement et les
exceptions.

Proposition de circuits, à confirmer avec les questions ci-dessous. La Direction RH approuve les
**décisions** (engager, promouvoir, sanctionner, clôturer la paie, adopter un plan, payer une
facture importante) et supervise les **opérations** (congés, absences, bons, inscriptions).

| Processus | Saisie | Validation | Approbation de la Direction RH | Suivi par la Direction RH |
| --- | --- | --- | --- | --- |
| **Congé annuel** | Administration du personnel | Chef de service | Non, sauf hors règle (au-delà du solde, période interdite) | Soldes de congés, taux d'absentéisme |
| **Congé de maladie** | Administration du personnel, avec le certificat médical | Chef de service | Non | Absences longues ou répétées (alerte) |
| **Heures supplémentaires** | Administration du personnel, avec l'autorisation préalable | Chef de service | Seulement au-delà d'un plafond mensuel ou du budget | Coût des heures supplémentaires par service |
| **Ajout d'un enfant à charge** | Administration du personnel, avec l'acte de naissance | Chef de service | Non : la règle est objective | Dossiers sans pièce justificative |
| **Engagement** | Gestion de carrière (dossier et contrat) | Chef de service | **Oui** : engage le budget et crée un lien juridique | Effectif par rapport au budget |
| **Promotion, changement de grade** | Gestion de carrière | Chef de service | **Oui** : décision formelle avec effet sur la paie | Promotions par année, équité entre services |
| **Sanction disciplinaire** | Gestion de carrière | Chef de service | **Oui**, souvent avec une commission | Nombre et nature des dossiers |
| **Paie mensuelle** | Rémunération calcule à partir des données validées | Chef de service Rémunération, sur l'état de contrôle | **Oui, la clôture** : une approbation pour toute la paie, pas bulletin par bulletin | Masse salariale, écarts inexpliqués (REM-12 à REM-17) |
| **Bons de soins** | Social | Chef de service Social | Non, bon par bon | Dépenses médicales, anomalies de facture |
| **Facture hospitalière** | Social, rapprochée des bons et de la grille tarifaire | Chef de service Social | **Oui**, si le montant à payer dépasse un seuil ou est contesté | Dépenses médicales mensuelles |
| **Plan de formation** | Formation | Chef de service Formation | **Oui**, une fois par an : c'est un budget | Budget consommé, sessions réalisées |
| **Inscription à une formation** | Formation | Chef de service Formation | Non, si elle figure au plan approuvé | — |
| **Sortie (démission, retraite, décès)** | Gestion de carrière | Chef de service | **Oui** : met fin au contrat et déclenche le décompte final | Départs à la retraite prévus (CAR-14) |

Dans un établissement public comme l'ARPTC, certaines de ces décisions sont en outre signées
au-dessus de la Direction RH, souvent par le Directeur général (voir Q22).

Conséquences attendues pour le SIRH :

- l'approbation est une règle **par type d'opération**, pas une relecture systématique ;
- les seuils (plafond d'heures supplémentaires, montant de facture) sont des **paramètres** ;
- la Direction RH a besoin d'une **vue des processus** (ce qui attend, où, depuis quand, les rejets
  et les exceptions), pas seulement des dossiers ;
- l'approbation de la paie repose sur l'**état de contrôle** : la Direction RH approuve les totaux
  et les exceptions, sans revoir chaque bulletin.

Questions à trancher :

- [ ] **Q20 — Opérations soumises à l'approbation de la Direction RH.** Pour quels types
  d'opération le circuit s'arrête-t-il au chef de service, et pour lesquels faut-il en plus
  l'approbation de la Direction RH ?
  - Concerne : TRA-01, TRA-02, section 3.
  - Hypothèse MVP : validation par le chef de service pour toutes les saisies ; approbation de la
    Direction RH en plus pour l'engagement, la promotion et le changement de grade, la sanction, la
    sortie, la clôture de la paie et le plan de formation. Les congés, absences, heures
    supplémentaires, dépendants, bons de soins et inscriptions à une formation prévue s'arrêtent au
    chef de service.
- [ ] **Q21 — Seuils de remontée à la Direction RH.** Au-delà de quels seuils une opération
  courante doit-elle être approuvée par la Direction RH : plafond mensuel d'heures supplémentaires
  par agent ou par service, montant d'une facture hospitalière, congé au-delà du solde, autres ?
  - Concerne : ADM-09, ADM-10, SOC-M-15, SOC-M-16.
  - Hypothèse MVP : seuils paramétrables, vides au départ (aucune remontée).
- [ ] **Q22 — Décisions signées hors du SIRH.** Quelles décisions relèvent du Directeur général ou
  d'une commission (engagement, promotion, sanction, révocation) ? Le SIRH doit-il faire circuler la
  demande jusqu'à la signature, ou seulement enregistrer la décision signée ?
  - Concerne : CAR-01, CAR-06, CAR-11, CAR-16.
  - Hypothèse MVP : le SIRH enregistre la décision signée (référence, date, signataire) avec sa
    pièce justificative.
- [ ] **Q23 — Saisie faite par un chef de service.** Qui valide une saisie faite par le chef de
  service lui-même, puisque l'auteur ne peut pas valider ?
  - Concerne : TRA-01, section 3 (séparation des tâches).
  - Hypothèse MVP : la Direction RH.
- [ ] **Q24 — Suppléants et délais.** Qui valide en l'absence du chef de service ? Au bout de
  combien de jours une saisie en attente doit-elle être signalée, ou passer au suppléant ?
  - Concerne : TRA-02, TRA-04.
  - Hypothèse MVP : suppléant désigné par paramétrage ; alerte après un délai paramétrable.
- [ ] **Q25 — Rejet et correction.** Après un rejet motivé, l'auteur corrige-t-il la même saisie et
  la soumet-il à nouveau, ou en crée-t-il une nouvelle ? La saisie rejetée reste-t-elle consultable ?
  - Concerne : TRA-01, TRA-10.
  - Hypothèse MVP : l'auteur corrige et soumet à nouveau la même saisie ; chaque rejet et son motif
    restent dans l'historique.
- [ ] **Q26 — Suivi des processus par la Direction RH.** Quelles vues attend-elle pour superviser
  sans tout revoir : saisies en attente par étape et par service, ancienneté des attentes, rejets et
  leurs motifs, exceptions (pièces manquantes, échéances dépassées, écarts de paie inexpliqués) ?
  - Concerne : TRA-08, REM-12 à REM-17.
  - Hypothèse MVP : un tableau des saisies en attente par étape et par service, avec leur ancienneté.

## 7. Points rédigés sans confirmation

Ces éléments du cahier des charges sont des propositions, non des réponses de l'ARPTC.

- [ ] **Q17 — Références légales.** Les textes cités en section 11 (Code du travail, CNSS, IPR, INPP,
  ONEM, Code du numérique) le sont de mémoire ; la Direction juridique doit confirmer la liste et les
  versions applicables.
- [ ] **Q18 — Seuils et durées proposés.** Planning de neuf mois en six phases, disponibilité de 99 %,
  délais de calcul, alertes de retraite à 12, 6 et 3 mois, conservation du journal d'audit 10 ans.
- [ ] **Q19 — Périmètre du MVP.** Quels modules et quelles exigences entrent dans la première version ?

## Déjà tranché

Pour mémoire, ces points ont reçu une réponse et sont intégrés au cahier des charges.

| Point | Réponse |
| --- | --- |
| Pièce pour le conjoint | Acte de mariage |
| Époux d'une agente | Non pris en compte comme dépendant |
| Limite d'âge des enfants | 25 ans |
| Nombre maximal d'enfants | Paramètre modifiable |
| Départ des 30 ans de carrière | Date d'engagement à l'ARPTC |
| Détachement | Compte dans les 30 ans de carrière |
| Mise en disponibilité | 2 ans, renouvelable une fois |
| Barèmes | Paramètres à renseigner dans le système |
| Devise et paiement | USD uniquement, par virement bancaire |
| Total brut du bulletin | Inclut la prime d'ancienneté |
| Base de l'IPR | Salaire de base seul |
| Pointeuse | Existe ; les absences sont saisies par l'Administration du personnel |
| Sites | Tous les sites |
| Hébergement | Serveurs de l'ARPTC |
| Portail agent | Versions ultérieures |
| Réalisation | Développement interne |
| Accès de l'Auditeur | Ne consulte ni la paie ni le détail des soins (17 novembre 2026) |
| Accès de la Direction RH | Consulte tous les modules RH, détail des soins compris (17 novembre 2026) |
