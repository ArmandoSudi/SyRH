# Cahier des charges — Système de gestion des ressources humaines de l'ARPTC

Nov 16, 2026 · @Armando

## 1. Contexte et objectifs

L'ARPTC veut un logiciel unique qui suit chaque agent de son engagement à sa sortie et qui alimente la paie sans ressaisie entre les services RH.

### 1.1 Contexte

L'Autorité de Régulation de la Poste et des Télécommunications du Congo (ARPTC) est une entreprise publique de droit congolais (RDC). Sa fonction Ressources humaines est organisée en cinq services : Rémunération, Social, Administration du personnel, Gestion de carrière et Formation.

Chaque service produit des données dont les autres dépendent. La Rémunération calcule la paie à partir des intérims, heures supplémentaires, promotions, congés de maternité, absences et allocations familiales transmis par les autres services. Le Social émet des bons de soins et contrôle la facture mensuelle de l'hôpital. Ces échanges sont la principale source d'erreurs et de retards.

### 1.2 Objectifs

1. Tenir un dossier unique par agent, partagé par les cinq services, de l'engagement à la sortie.
2. Transmettre automatiquement à la paie les événements validés par les autres services.
3. Expliquer tout écart de salaire d'un mois à l'autre, agent par agent.
4. Contrôler la facture de l'hôpital à partir des bons émis et de la grille tarifaire.
5. Anticiper les échéances de carrière : annuités, fins de contrat, départs à la retraite.
6. Garder la trace de chaque saisie, modification et validation.

### 1.3 Terminologie

| Terme | Définition |
| --- | --- |
| Agent | Personne liée à l'ARPTC par un contrat de travail |
| Dépendant | Épouse d'un agent, ou enfant d'un agent ou d'une agente, enregistré sur pièce justificative |
| Élément variable | Donnée du mois qui modifie la paie : absence, heure supplémentaire, intérim, prime |
| Bon de soins | Document émis par le service Social autorisant une prise en charge à l'hôpital |
| État de contrôle | Rapport comparant le salaire du mois à celui du mois précédent, par agent |
| SIRH | Le logiciel objet du présent cahier des charges |

## 2. Périmètre

Le SIRH couvre tout le cycle de vie de l'agent, en cinq modules métier correspondant aux cinq services RH, plus un socle commun.

### 2.1 Cycle de vie de l'agent

1. **Engagement** : création du dossier, du contrat et de l'affectation par la Gestion de carrière.
2. **Évolution professionnelle** : avancements, promotions, mutations, intérims, formations, annuités.
3. **Évolution sociale** : mariage, naissances, décès d'un dépendant, avec effet sur les allocations familiales et la couverture médicale.
4. **Vie courante** : présences, absences, congés, heures supplémentaires, soins médicaux, paie mensuelle.
5. **Sortie** : décès, démission ou retraite, puis clôture du dossier et calcul du décompte final.

### 2.2 Motifs de sortie

| Motif | Déclencheur | Traitement attendu |
| --- | --- | --- |
| Retraite pour ancienneté | 30 ans de carrière atteints | Alerte anticipée, décision de mise à la retraite, décompte final |
| Retraite pour limite d'âge | 65 ans atteints | Alerte anticipée, décision de mise à la retraite, décompte final |
| Démission | Lettre de démission de l'agent | Enregistrement du préavis, décompte final |
| Décès | Acte de décès | Clôture du dossier, décompte final au profit des ayants droit |

La retraite intervient dès que la première des deux conditions est remplie. Les 30 ans de carrière se comptent à partir de la date d'engagement à l'ARPTC. Le référentiel des motifs reste paramétrable pour accueillir d'autres cas (licenciement, fin de contrat à durée déterminée).

### 2.3 Suspensions de carrière

Deux positions suspendent la carrière sans y mettre fin ; pendant leur durée, l'agent ne perçoit ni rémunération ni avantage de l'ARPTC.

| Position | Cas | Durée | Effet dans le SIRH |
| --- | --- | --- | --- |
| Mise en disponibilité | Décision de mise en disponibilité | 2 ans, renouvelable une fois, soit 4 ans au plus | Paie, allocations familiales et bons de soins suspendus ; alerte avant l'échéance ; refus d'un second renouvellement |
| Détachement | Agent appelé à travailler dans une autre entité de l'État | Durée fixée par la décision de détachement | Paie, allocations familiales et bons de soins suspendus ; alerte avant l'échéance |

À l'échéance, la Gestion de carrière enregistre la reprise de service, qui réactive l'agent dans tous les modules, ou la sortie définitive. La période de détachement compte dans les 30 ans de carrière.

### 2.4 Inclus

- Dossier de l'agent et de ses dépendants
- Gestion de carrière : engagement, promotions, sorties
- Administration du personnel : présences, absences, heures supplémentaires, stagiaires, journaliers
- Rémunération : calcul de la paie, bulletins, état de contrôle, déclarations
- Social : bons de soins, grille tarifaire, contrôle des factures de l'hôpital
- Formation : sessions et historique par agent
- Gestion électronique des pièces justificatives, alertes, rapports, journal d'audit

### 2.5 Exclus

- Comptabilité générale et trésorerie : le SIRH fournit des fichiers d'export, sans tenir les comptes
- Recrutement en amont de l'engagement : appels à candidatures, sélection
- Dossier médical de l'agent : le SIRH ne conserve que les données nécessaires au contrôle des factures

## 3. Acteurs et profils

Chaque service saisit ses propres données et consulte celles des autres ; aucune donnée n'entre en paie sans validation de son service d'origine.

| Profil | Rôle dans le SIRH | Droits principaux |
| --- | --- | --- |
| Gestion de carrière | Crée l'agent, enregistre promotions et sorties | Écriture sur dossier, contrat, grade, fonction |
| Administration du personnel | Tient présences, absences, heures supplémentaires, dépendants, stagiaires, journaliers | Écriture sur pointage, congés, dépendants |
| Rémunération | Calcule, contrôle et clôture la paie | Écriture sur rubriques et bulletins ; lecture des éléments variables |
| Social | Émet les bons de soins, contrôle les factures | Écriture sur bons, grille tarifaire, factures |
| Formation | Planifie et enregistre les formations | Écriture sur sessions et participations |
| Chef de service RH | Valide les saisies de son service | Validation, rejet motivé |
| Direction RH | Supervise, approuve la paie et les décisions de carrière | Approbation, tableaux de bord, tous rapports |
| Auditeur / contrôle interne | Vérifie les opérations | Lecture seule, journal d'audit |
| Administrateur système | Gère comptes, profils et paramètres | Administration technique, sans accès aux montants de paie |
| Agent (version ultérieure) | Consulte son dossier et ses bulletins, introduit ses demandes | Lecture de ses propres données |

Règles communes :

- **Séparation des tâches** : la personne qui saisit une donnée ne la valide pas.
- **Moindre privilège** : un profil ne voit que les données nécessaires à son travail. Les salaires sont visibles de la Rémunération et de la Direction RH seulement.
- **Profils paramétrables** : l'administrateur peut créer des profils et ajuster les droits sans développement.

## 4. Socle commun : référentiels et dossier de l'agent

Le dossier de l'agent est la source unique de vérité ; tous les modules le lisent et aucun ne le duplique.

### 4.1 Référentiels paramétrables

- Structure organisationnelle : directions, départements, services, bureaux, sites
- Catégories, grades, échelons et fonctions, avec la grille salariale associée
- Types de contrat : durée indéterminée, durée déterminée, stage, journalier
- Types d'absence et de congé, avec leur effet sur la paie
- Rubriques de paie : gains, retenues, cotisations, bases et formules
- Types de pièces justificatives, motifs de sortie, jours fériés légaux
- Banques : dénomination, code, modèle du fichier de virement

### 4.2 Contenu du dossier de l'agent

| Rubrique | Données |
| --- | --- |
| Identité | Matricule unique, nom, postnom, prénom, sexe, date et lieu de naissance, nationalité, photo, pièce d'identité |
| Coordonnées | Adresse, téléphone, courriel, personne à contacter en cas d'urgence |
| État civil | Situation matrimoniale, dépendants |
| Contrat | Type, date d'engagement, période d'essai, date de fin éventuelle |
| Position | Direction, service, fonction, grade, échelon, supérieur hiérarchique |
| Paie | Salaire de base, primes fixes, banque et numéro de compte bancaire, numéro d'affiliation à la CNSS |
| Parcours | Diplômes, expériences antérieures, formations, promotions, sanctions, distinctions |
| Pièces | Copies numérisées de tous les justificatifs |

### 4.3 Exigences

| Réf. | Exigence |
| --- | --- |
| SOC-01 | Attribuer à chaque agent un matricule unique, jamais réutilisé |
| SOC-02 | Conserver l'historique daté de toute donnée qui évolue : grade, fonction, salaire, affectation, état civil |
| SOC-03 | Dater chaque événement par sa date d'effet, distincte de sa date de saisie, pour permettre les rappels de paie |
| SOC-04 | Rattacher à chaque événement la pièce justificative numérisée qui le fonde |
| SOC-05 | Afficher une fiche de synthèse de l'agent, imprimable, avec sa chronologie complète |
| SOC-06 | Rechercher un agent par matricule, nom, service, grade, fonction ou statut |
| SOC-07 | Calculer automatiquement l'âge et l'ancienneté à partir des dates de naissance et d'engagement |

## 5. Module Gestion de carrière

Ce module ouvre le dossier de l'agent à son engagement, enregistre chaque évolution de grade ou de fonction et clôt le dossier à la sortie.

### 5.1 Engagement

| Réf. | Exigence |
| --- | --- |
| CAR-01 | Créer l'agent au début de son contrat : identité, contrat, affectation, grade, salaire de base |
| CAR-02 | Exiger les pièces d'engagement définies au référentiel (contrat signé, pièce d'identité, diplômes) avant validation |
| CAR-03 | Suivre la période d'essai et alerter avant son échéance |
| CAR-04 | Suivre les contrats à durée déterminée et alerter avant leur terme |
| CAR-05 | Rendre l'agent validé immédiatement disponible pour les autres modules, dont la paie |

### 5.2 Évolution professionnelle

| Réf. | Exigence |
| --- | --- |
| CAR-06 | Enregistrer une promotion ou un avancement sur la base du document de promotion : ancien et nouveau grade, date d'effet, référence de la décision |
| CAR-07 | Transmettre à la paie le nouveau salaire de base à la date d'effet, avec calcul du rappel si la décision est rétroactive |
| CAR-08 | Enregistrer mutations et changements de fonction ; enregistrer détachements et mises en disponibilité avec leur décision et leurs dates, suspendre paie, allocations et bons de soins pendant la période, alerter avant l'échéance et enregistrer la reprise de service |
| CAR-09 | Enregistrer les intérims : poste occupé, titulaire remplacé, dates de début et de fin, décision ; transmettre la prime d'intérim à la paie pour la période exacte |
| CAR-10 | Calculer l'ancienneté et déclencher la prime d'annuité à chaque date anniversaire, selon le barème paramétré |
| CAR-11 | Enregistrer sanctions disciplinaires et distinctions, avec leur effet éventuel sur la paie |
| CAR-12 | Enregistrer les évaluations périodiques de l'agent |
| CAR-13 | Lister les agents éligibles à un avancement selon les critères paramétrés |

### 5.3 Sortie

| Réf. | Exigence |
| --- | --- |
| CAR-14 | Signaler 12, 6 et 3 mois à l'avance les agents qui atteindront 30 ans de carrière ou 65 ans d'âge |
| CAR-15 | Produire la liste prévisionnelle des départs à la retraite par année |
| CAR-16 | Enregistrer la sortie : motif, date d'effet, pièce justificative (décision de retraite, lettre de démission, acte de décès) |
| CAR-17 | Transmettre à la paie les éléments du décompte final : prorata du mois, congés non pris, indemnités dues |
| CAR-18 | En cas de décès, identifier les ayants droit à partir des dépendants enregistrés |
| CAR-19 | Désactiver l'agent sorti dans tous les modules (paie, bons de soins, pointage) sans supprimer son dossier |
| CAR-20 | Éditer attestation de service, certificat de fin de service et autres documents de sortie depuis des modèles |

## 6. Module Administration du personnel

Ce module tient le temps de travail des agents, leurs dépendants, ainsi que les stagiaires et les journaliers ; il est le premier fournisseur d'éléments variables de la paie.

### 6.1 Présences et absences

| Réf. | Exigence |
| --- | --- |
| ADM-01 | Reprendre les présences depuis la pointeuse existante, par interface ou import de fichier ; les absences sont renseignées par le bureau Administration du personnel |
| ADM-02 | Enregistrer les absences par type : congé annuel, congé de circonstance, maladie, maternité, mission, absence autorisée, absence injustifiée |
| ADM-03 | Exiger la pièce justificative prévue pour chaque type (certificat médical, ordre de mission) |
| ADM-04 | Gérer les droits à congé annuel : acquisition, prise, solde, report, planning par service |
| ADM-05 | Gérer le congé de maternité : dates, durée légale, certificat ; transmission à la paie de la période, pendant laquelle la composante transport du salaire n'est pas versée |
| ADM-06 | Suivre les absences pour maladie et leur cumul, avec transmission à la paie de la période, pendant laquelle la composante transport du salaire n'est pas versée |
| ADM-07 | Transmettre à la paie les absences non rémunérées du mois, après validation |
| ADM-08 | Produire l'état mensuel de présence par agent et par service, et le taux d'absentéisme |

### 6.2 Heures supplémentaires

| Réf. | Exigence |
| --- | --- |
| ADM-09 | Enregistrer les heures supplémentaires par agent, par date, avec l'autorisation préalable du responsable |
| ADM-10 | Classer les heures selon les tranches et majorations paramétrées : jour ouvrable, nuit, repos hebdomadaire, jour férié |
| ADM-11 | Transmettre à la paie le décompte mensuel validé |

### 6.3 Dépendants

| Réf. | Exigence |
| --- | --- |
| ADM-12 | Enregistrer l'épouse d'un agent à réception de l'acte de mariage ; l'époux d'une agente n'est pas pris en compte comme dépendant |
| ADM-13 | Enregistrer chaque enfant à réception de son acte de naissance |
| ADM-14 | Refuser la validation d'un dépendant sans pièce numérisée jointe |
| ADM-15 | Enregistrer la fin de la qualité de dépendant : décès, divorce, enfant atteignant 25 ans |
| ADM-16 | Alerter avant qu'un enfant atteigne 25 ans, âge auquel il cesse d'être à charge, et le retirer alors des allocations familiales et des bons de soins |
| ADM-17 | Transmettre à la paie le nombre de dépendants ouvrant droit aux allocations familiales, à la date d'effet, dans la limite d'un nombre maximal d'enfants pris en charge, paramétrable |
| ADM-18 | Rendre les dépendants validés éligibles aux bons de soins du module Social |

### 6.4 Stagiaires et journaliers

| Réf. | Exigence |
| --- | --- |
| ADM-19 | Enregistrer les stagiaires : identité, établissement d'origine, type de stage, service d'accueil, encadreur, dates, prime éventuelle |
| ADM-20 | Alerter avant la fin d'un stage et éditer l'attestation de stage |
| ADM-21 | Enregistrer les journaliers : identité, service, tâche, taux journalier, jours prestés |
| ADM-22 | Transmettre à la paie l'état mensuel des jours prestés par les journaliers et des primes de stage |
| ADM-23 | Tenir stagiaires et journaliers dans des registres distincts de celui des agents, avec passage possible au statut d'agent sans ressaisie |

## 7. Module Rémunération

Ce module calcule la paie mensuelle à partir des données validées par les autres services et justifie chaque écart de salaire par rapport au mois précédent.

### 7.1 Données reçues des autres modules

| Donnée | Service émetteur | Effet sur la paie |
| --- | --- | --- |
| Engagement | Gestion de carrière | Entrée en paie, prorata du premier mois |
| Promotion, avancement | Gestion de carrière | Nouveau salaire de base, rappel éventuel |
| Intérim | Gestion de carrière | Prime d'intérim sur la période |
| Annuité | Gestion de carrière (calcul automatique) | Prime d'annuité |
| Sortie | Gestion de carrière | Décompte final, arrêt de la paie |
| Absences non rémunérées | Administration du personnel | Retenue |
| Maladie, maternité | Administration du personnel | Composante transport non versée pendant la période |
| Heures supplémentaires | Administration du personnel | Majoration |
| Dépendants | Administration du personnel | Allocations familiales, charges de famille pour l'impôt |
| Jours prestés, primes de stage | Administration du personnel | Paie des journaliers et des stagiaires |
| Quote-part de soins à charge de l'agent | Social | Retenue éventuelle |

### 7.2 Calcul de la paie

| Réf. | Exigence |
| --- | --- |
| REM-01 | Paramétrer les rubriques de paie sans développement : libellé, nature (gain, retenue, cotisation), base, formule, caractère imposable et cotisable |
| REM-02 | Ouvrir une période de paie mensuelle et y intégrer automatiquement les éléments variables validés |
| REM-03 | Calculer salaire brut, cotisations sociales, impôt professionnel sur les rémunérations, autres retenues et net à payer, selon la législation congolaise en vigueur |
| REM-04 | Dater les barèmes et les taux pour appliquer un changement légal à partir d'une date d'effet |
| REM-05 | Gérer avances, acomptes, prêts et leurs remboursements échelonnés |
| REM-06 | Calculer les rappels nés d'une décision rétroactive |
| REM-07 | Calculer les primes périodiques paramétrées (gratification, treizième mois, prime de fin d'année) |
| REM-08 | Calculer le décompte final d'un agent sortant |
| REM-09 | Permettre une simulation de paie avant clôture, pour un agent ou pour tous |
| REM-10 | Soumettre la paie à un circuit de validation, puis la clôturer ; une paie clôturée n'est plus modifiable et toute correction passe par le mois suivant |
| REM-11 | Calculer et payer la paie en USD uniquement, par virement bancaire |

### 7.3 État de contrôle

| Réf. | Exigence |
| --- | --- |
| REM-12 | Comparer, agent par agent, le salaire du mois à celui du mois précédent, rubrique par rubrique |
| REM-13 | Rattacher automatiquement chaque écart à l'événement qui le cause : annuité, intérim, promotion, maternité, maladie, absence, heures supplémentaires, dépendant, prêt, rappel |
| REM-14 | Signaler en anomalie tout écart sans événement justificatif ; la clôture est bloquée tant qu'une anomalie n'est ni corrigée ni justifiée par écrit |
| REM-15 | Lister les entrées et les sorties du mois, et rapprocher la masse salariale totale de celle du mois précédent |
| REM-16 | Filtrer l'état par service, par cause d'écart et par seuil de montant ; l'exporter en PDF et Excel |
| REM-17 | Permettre la comparaison entre deux périodes quelconques |

### 7.4 Éditions

| Réf. | Exigence |
| --- | --- |
| REM-18 | Éditer le bulletin de paie individuel, en PDF, avec envoi possible par courriel |
| REM-19 | Éditer le livre de paie, le journal de paie et l'état récapitulatif par rubrique et par service |
| REM-20 | Générer, pour chaque banque, le fichier Excel qui accompagne l'ordre de virement de l'employeur : matricule, nom, numéro de compte, montant net en USD de chaque agent, nombre d'agents et montant total |
| REM-21 | Produire les états déclaratifs destinés à la CNSS, à la DGI, à l'INPP et à l'ONEM |
| REM-22 | Produire le fichier d'écritures de paie destiné à la comptabilité |

### 7.5 Barèmes et composition du salaire

Tous les barèmes sont des paramètres que le service Rémunération renseigne et met à jour dans le SIRH, sans développement.

| Réf. | Exigence |
| --- | --- |
| REM-23 | Paramétrer chaque barème avec sa date d'effet : salaire de base, prime d'ancienneté, logement, transport, allocations familiales, prime d'intérim, majorations des heures supplémentaires, cotisation syndicale, taux de CNSS et d'IPR |
| REM-24 | Permettre qu'une composante du salaire dépende du grade de l'agent : le barème porte alors un montant par grade, et un changement de grade applique le nouveau montant à la date d'effet |
| REM-25 | Calculer le salaire de base par jours prestés multipliés par un taux journalier, sur une base mensuelle paramétrable (26 jours sur le bulletin actuel) |
| REM-26 | Calculer la prime d'ancienneté à partir du nombre d'années d'ancienneté et du barème ; elle entre dans le total brut mais pas dans la base de l'IPR, qui se calcule sur le seul salaire de base |
| REM-27 | Ne pas verser la composante transport pour les jours de maladie et de congé de maternité |
| REM-28 | Tenir le référentiel des banques et rattacher à chaque agent sa banque et son numéro de compte ; bloquer la mise en paiement d'un agent sans compte bancaire validé |

### 7.6 Modèle du bulletin de paie

Le SIRH édite un bulletin d'une page, bilingue français / anglais, en USD, conforme au modèle actuel de l'ARPTC.

| Zone | Contenu |
| --- | --- |
| En-tête | Dénomination et logo de l'ARPTC, Direction des Ressources humaines, adresse, titre « Bulletin de paie / Pay slip », mois de paie, date d'impression |
| Identification | Nom, matricule, numéro d'affiliation CNSS (ou mention « en cours »), classification, fonction, date d'engagement, ancienneté en années, état civil, nombre d'enfants à charge |
| Gains | Une ligne par gain : description, jours ou heures, taux, montant. Salaire de base, prime d'ancienneté, puis les autres gains du mois |
| Total brut | Somme de tous les gains, prime d'ancienneté comprise ; le bulletin actuel l'omet par erreur, le SIRH corrige ce point |
| Retenues | CNSS quote-part ouvrière, base imposable (égale au seul salaire de base), IPR calculé sur cette base, cotisation syndicale, autres retenues du mois |
| Total retenues | Somme des retenues |
| Avantages légaux | Logement et transport : taux, montant |
| Net à payer | Gains et avantages légaux, moins le total des retenues |
| Pied de page | Signature de l'agent pour acquit, date, cachet de l'employeur |

| Réf. | Exigence |
| --- | --- |
| REM-29 | Éditer le bulletin selon ce modèle, pour un agent ou par lot pour tout l'effectif, en PDF |
| REM-30 | N'afficher que les rubriques non nulles du mois, dans un ordre paramétrable |
| REM-31 | Rééditer à l'identique le bulletin d'un mois clôturé, même si les barèmes ou le dossier de l'agent ont changé depuis |

## 8. Module Social

Ce module émet les bons de soins et vérifie la facture mensuelle de l'hôpital, ligne par ligne, contre les bons émis et la grille tarifaire.

### 8.1 Bons de soins

| Réf. | Exigence |
| --- | --- |
| SOC-M-01 | Émettre un bon numéroté pour un agent actif ou l'un de ses dépendants validés ; refuser tout autre bénéficiaire |
| SOC-M-02 | Porter sur le bon : numéro unique, bénéficiaire, agent de rattachement, hôpital, type de soin demandé, date d'émission, durée de validité, émetteur |
| SOC-M-03 | Imprimer le bon avec un code de vérification (QR code ou code-barres) |
| SOC-M-04 | Suivre le statut du bon : émis, utilisé, facturé, expiré, annulé |
| SOC-M-05 | Appliquer les plafonds et les exclusions de prise en charge paramétrés, par agent ou par bénéficiaire |
| SOC-M-06 | Permettre la régularisation d'une urgence par un bon émis après les soins, signalé comme tel et soumis à validation |
| SOC-M-07 | Gérer plusieurs hôpitaux et prestataires conventionnés (pharmacie, laboratoire, optique) |

### 8.2 Grille tarifaire

| Réf. | Exigence |
| --- | --- |
| SOC-M-08 | Enregistrer la grille tarifaire de chaque hôpital : code de l'acte, libellé, catégorie, prix unitaire, devise |
| SOC-M-09 | Importer la grille depuis un fichier Excel ou CSV fourni par l'hôpital |
| SOC-M-10 | Dater chaque version de la grille ; la facture est contrôlée avec la grille en vigueur à la date des soins |

### 8.3 Contrôle de la facture mensuelle

| Réf. | Exigence |
| --- | --- |
| SOC-M-11 | Saisir ou importer la facture de l'hôpital, ligne par ligne : numéro de bon, patient, date, acte, quantité, prix unitaire, montant |
| SOC-M-12 | Rapprocher automatiquement chaque ligne d'un bon émis |
| SOC-M-13 | Comparer le prix facturé de chaque acte au prix de la grille tarifaire |
| SOC-M-14 | Produire l'état des écarts avec le montant contesté par ligne et au total |
| SOC-M-15 | Calculer le montant à payer après contrôle et le transmettre pour validation puis paiement |
| SOC-M-16 | Éditer le relevé des contestations à adresser à l'hôpital |

Anomalies détectées par le contrôle :

- Ligne facturée sans bon correspondant
- Bon facturé plusieurs fois
- Bon annulé ou expiré à la date des soins
- Patient différent du bénéficiaire du bon
- Acte absent de la grille tarifaire
- Prix unitaire supérieur au prix de la grille
- Erreur de calcul entre quantité, prix unitaire et montant
- Total de la facture différent de la somme des lignes

### 8.4 Suivi

| Réf. | Exigence |
| --- | --- |
| SOC-M-17 | Produire la consommation médicale par agent, par bénéficiaire, par hôpital et par période |
| SOC-M-18 | Transmettre à la paie la quote-part éventuelle à charge de l'agent |
| SOC-M-19 | Enregistrer les autres prestations sociales paramétrées : frais funéraires, aides exceptionnelles |
| SOC-M-20 | Limiter au seul service Social l'accès au détail des soins reçus par un patient |

## 9. Module Formation

Ce module enregistre les formations dont bénéficient les agents et en conserve l'historique dans leur dossier.

| Réf. | Exigence |
| --- | --- |
| FOR-01 | Recueillir les besoins de formation exprimés par les services |
| FOR-02 | Établir le plan annuel de formation avec son budget prévisionnel |
| FOR-03 | Tenir le catalogue des formations et des organismes formateurs |
| FOR-04 | Enregistrer chaque session : intitulé, organisme, lieu (local ou à l'étranger), dates, durée, coût, participants |
| FOR-05 | Enregistrer pour chaque participant la présence, le résultat et le certificat ou diplôme obtenu, avec la pièce numérisée |
| FOR-06 | Signaler à l'Administration du personnel l'absence de l'agent en formation, pour qu'elle ne soit pas comptée comme injustifiée |
| FOR-07 | Alimenter le dossier de l'agent avec les formations suivies et les compétences acquises, consultables par la Gestion de carrière |
| FOR-08 | Enregistrer l'évaluation de la formation par le participant et par son supérieur |
| FOR-09 | Suivre le budget consommé par rapport au budget prévu |
| FOR-10 | Produire les statistiques : agents formés, heures de formation, coût par service, par sexe et par catégorie |

## 10. Fonctions transversales

Ces fonctions s'appliquent à tous les modules.

| Réf. | Fonction | Exigence |
| --- | --- | --- |
| TRA-01 | Circuit de validation | Toute donnée ayant un effet sur la paie suit le circuit saisie, validation, intégration ; un rejet est motivé et renvoyé à l'auteur |
| TRA-02 | Circuit de validation | Les circuits (étapes, validateurs, suppléants) sont paramétrables par type d'opération |
| TRA-03 | Pièces justificatives | Numériser, classer et consulter les pièces depuis le dossier de l'agent ; formats PDF et image |
| TRA-04 | Alertes | Notifier dans l'application et par courriel les échéances : fin d'essai, fin de contrat, fin de stage, annuité, retraite, limite d'âge d'un enfant, fin d'intérim, bon expiré |
| TRA-05 | Calendrier de paie | Fixer une date limite mensuelle de transmission des éléments variables ; ce qui arrive après est reporté au mois suivant |
| TRA-06 | Rapports | Fournir les rapports standard de chaque module, exportables en PDF et Excel |
| TRA-07 | Rapports | Offrir un générateur de listes : choix des colonnes, filtres, tris, sauvegarde du modèle |
| TRA-08 | Tableau de bord | Afficher effectif, répartition par sexe, âge, grade et service, masse salariale, absentéisme, dépenses médicales, départs prévus |
| TRA-09 | Éditions | Générer attestations, décisions et courriers à partir de modèles modifiables par les RH |
| TRA-10 | Journal d'audit | Enregistrer pour chaque création, modification, validation et suppression : auteur, date, heure, ancienne et nouvelle valeur ; journal non modifiable |
| TRA-11 | Langue | Interface, éditions et documentation en français |

## 11. Exigences non fonctionnelles

Le SIRH traite des données personnelles, médicales et salariales : la confidentialité et la traçabilité priment sur toute autre exigence technique.

| Réf. | Domaine | Exigence |
| --- | --- | --- |
| NF-01 | Accès | Authentification individuelle par identifiant et mot de passe robuste ; double authentification pour les profils sensibles ; verrouillage après échecs répétés |
| NF-02 | Accès | Droits par profil et par périmètre (module, service, type de donnée) ; déconnexion automatique après inactivité |
| NF-03 | Confidentialité | Chiffrement des échanges (HTTPS/TLS) et des données sensibles au repos : salaires, données médicales, pièces d'identité |
| NF-04 | Données personnelles | Conformité à la législation congolaise sur la protection des données personnelles ; hébergement sur les serveurs de l'ARPTC |
| NF-05 | Traçabilité | Journal d'audit complet, horodaté, inaltérable, conservé au moins 10 ans |
| NF-06 | Disponibilité | Service disponible à 99 % pendant les heures ouvrables ; aucune interruption planifiée pendant la période de paie |
| NF-07 | Sauvegarde | Sauvegarde quotidienne automatique, copie hors site, test de restauration trimestriel ; perte de données maximale d'un jour, reprise en moins de 8 heures |
| NF-08 | Performance | Affichage d'un écran courant en moins de 3 secondes ; calcul de la paie de tout l'effectif en moins de 15 minutes |
| NF-09 | Capacité | Dimensionnement pour l'effectif actuel et sa croissance sur 10 ans, historique compris |
| NF-10 | Ergonomie | Application web utilisable depuis un navigateur courant, sans installation sur le poste ; écrans cohérents d'un module à l'autre |
| NF-11 | Continuité | Accès depuis tous les sites de l'ARPTC, siège et représentations provinciales, par le réseau de l'ARPTC |
| NF-12 | Évolutivité | Règles de gestion, barèmes, rubriques et circuits modifiables par paramétrage |
| NF-13 | Archivage | Dossiers des agents sortis conservés et consultables pendant la durée légale ; aucune suppression physique |

### Cadre légal de référence

Les règles de calcul et de gestion doivent respecter les textes en vigueur en RDC, notamment :

- le Code du travail (loi n° 015/2002, modifiée en 2016) et ses mesures d'application ;
- la législation sur la sécurité sociale et les cotisations à la CNSS ;
- la législation fiscale sur l'impôt professionnel sur les rémunérations (IPR) ;
- les contributions patronales à l'INPP et à l'ONEM ;
- le Code du numérique pour la protection des données personnelles ;
- les textes propres à l'ARPTC : statut du personnel, règlement d'entreprise, convention collective, barème salarial.

Ces références sont citées de mémoire, sans vérification sur les textes officiels ; la Direction juridique de l'ARPTC doit en confirmer la liste et les versions applicables. En cas de divergence, les textes propres à l'ARPTC plus favorables à l'agent s'appliquent.

## 12. Mise en œuvre

Développé en interne par l'ARPTC, le projet se déroule en six phases sur environ neuf mois, avec une paie en double (ancien et nouveau système) pendant au moins deux mois avant la bascule.

### 12.1 Exigences techniques

| Réf. | Exigence |
| --- | --- |
| TEC-01 | Application web en architecture trois tiers : navigateur, serveur applicatif, base de données relationnelle |
| TEC-02 | Technologies ouvertes, documentées et maintenables localement ; l'équipe de développement de l'ARPTC documente ses choix |
| TEC-03 | Trois environnements distincts : test, formation, production |
| TEC-04 | Interfaces d'échange (API et fichiers) avec la pointeuse, la comptabilité, les banques et la messagerie |
| TEC-05 | Import et export aux formats Excel, CSV et PDF |
| TEC-06 | Code source versionné dans un dépôt interne de l'ARPTC, avec revue de code et tests automatisés |

### 12.2 Reprise des données

| Réf. | Exigence |
| --- | --- |
| REP-01 | Inventorier les sources existantes : fichiers Excel, dossiers papier, logiciel de paie actuel |
| REP-02 | Reprendre les dossiers des agents actifs, leurs dépendants et leur historique de carrière |
| REP-03 | Reprendre au moins 12 mois d'historique de paie, pour l'état de contrôle et les cumuls annuels |
| REP-04 | Reprendre les soldes de congés, les prêts en cours, les bons de soins non encore facturés et la grille tarifaire |
| REP-05 | Faire valider les données reprises par chaque service avant la mise en production |

### 12.3 Phases

| Phase | Contenu | Durée indicative | Livrable |
| --- | --- | --- | --- |
| 1. Cadrage | Ateliers avec les cinq services, recueil des règles de gestion | 1 mois | Spécifications fonctionnelles détaillées validées |
| 2. Socle et carrière | Référentiels, dossier de l'agent, module Gestion de carrière | 1,5 mois | Version 1 en environnement de test |
| 3. Administration et paie | Modules Administration du personnel et Rémunération, état de contrôle | 2,5 mois | Version 2 en environnement de test |
| 4. Social et formation | Modules Social et Formation, rapports, tableau de bord | 1,5 mois | Version 3 en environnement de test |
| 5. Reprise et recette | Reprise des données, recette, paie en double | 2 mois | Procès-verbal de recette |
| 6. Déploiement | Formation des utilisateurs, mise en production, assistance au démarrage | 0,5 mois | Procès-verbal de mise en service |

### 12.4 Recette

- Chaque exigence du présent document fait l'objet d'au moins un cas de test, rédigé avec le service concerné.
- La paie calculée par le SIRH est comparée à la paie officielle pendant deux mois consécutifs ; tout écart est expliqué avant la bascule.
- Le contrôle d'une facture réelle de l'hôpital est rejoué dans le SIRH et comparé au contrôle manuel.
- La recette est prononcée sans anomalie bloquante et avec un plan de correction daté des anomalies mineures.

### 12.5 Livrables et accompagnement

- Logiciel installé, paramétré et code source
- Spécifications détaillées, dossier d'architecture, modèle de données
- Manuels d'utilisation par profil, manuel d'administration et d'exploitation
- Formation des utilisateurs de chaque service et des administrateurs
- Maintenance corrective et évolutive assurée par l'équipe de développement de l'ARPTC, avec des délais d'intervention convenus avec la Direction RH

## 13. Points à confirmer par l'ARPTC

Ces questions restent ouvertes ; leurs réponses fixent des règles de gestion que le présent document laisse paramétrables.

- [ ] Enfants à charge : prolongation au-delà de 25 ans pour études ?
- [ ] Autres motifs de sortie définitive à prévoir : licenciement, fin de contrat, révocation, inaptitude ? La période de mise en disponibilité compte-t-elle dans les 30 ans de carrière, comme celle de détachement ?
- [ ] Maladie et maternité : le transport est-il retenu au prorata des jours d'absence ? Le reste du salaire est-il maintenu en totalité, sans limite de durée ?
- [ ] Plafonds de prise en charge médicale et quote-part éventuelle à charge de l'agent
- [ ] Nombre d'hôpitaux et de prestataires conventionnés ; format dans lequel ils transmettent facture et grille tarifaire
- [ ] Logiciel de paie et logiciel comptable existants à interfacer ; mode de liaison avec la pointeuse (interface directe ou import de fichier)
- [ ] Effectif chiffré : nombre d'agents, de stagiaires, de journaliers et d'utilisateurs du SIRH

Questions soulevées par le bulletin de paie fourni :

- [ ] La prime d'ancienneté du bulletin est-elle la prime d'annuité ? Selon quel barème évolue-t-elle ?
- [ ] Quelles composantes dépendent du grade : salaire de base, logement, transport, autres ?
- [ ] CNSS : la quote-part ouvrière est-elle nulle tant que l'affiliation est « en cours », puis régularisée ?
- [ ] Format du matricule : faut-il le générer automatiquement sous la forme préfixe / numéro d'ordre / année d'engagement ?
- [ ] Liste complète des autres gains et retenues pouvant figurer sur un bulletin : intérim, heures supplémentaires, allocations familiales, prêts, avances
