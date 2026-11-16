# Questions ouvertes — SIRH ARPTC

État au 16 novembre 2026. Ces questions n'ont pas encore de réponse ; elles complètent le
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
- [ ] **Q3 — Mise en disponibilité et 30 ans de carrière.** La période de mise en disponibilité
  compte-t-elle dans les 30 ans, comme celle de détachement ?
  - Concerne : section 2.3, CAR-14, SOC-07.
  - Hypothèse MVP : indicateur « compte dans l'ancienneté » par type de suspension.
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

## 6. Points rédigés sans confirmation

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
