import gurobipy as gp
from gurobipy import GRB

Dictionnaire_cours = {
    "A" : 32,
    "B" : 0,
    "C" : -28,
    "D" : 36,
    "E" : 48,
    "F" : -35,
    "G" : -42
}

def def_pros_cons_neutrals(dictionnaire):
    """Identifie les critères positifs (pros), négatifs (cons) et neutres."""
    pros = []
    cons = []
    neutrals = []
    for cours1, valeur1 in dictionnaire.items():
        if valeur1 > 0 :
            pros.append(cours1)
        elif valeur1 < 0 :
            cons.append(cours1)
        else:
            neutrals.append(cours1)
    return pros, cons, neutrals

def def_trade_offs(dictionnaire):
    """Calcule tous les trade-offs possibles (paires pro-con avec somme positive)."""
    pros, cons, neutrals = def_pros_cons_neutrals(dictionnaire)
    trade_offs = []
    for pro in pros:
        for con in cons:
            if dictionnaire[pro] + dictionnaire[con] > 0:
                trade_offs.append([pro, con])
    return trade_offs

def exist_explication_1_1_avec_solveur(dictionnaire):
    """
    Formule un programme linéaire pour trouver une explication 1-1 de x ≻ y.
    
    Variables de décision: z_ij binaires (1 si le trade-off (i,j) est sélectionné)
    Contraintes:
    - Chaque con doit être couvert exactement une fois
    - Chaque pro peut être utilisé au plus une fois
    - Seuls les trade-offs valides (somme > 0) peuvent être sélectionnés
    
    Retourne: (existe, explication ou certificat)
    """
    pros, cons, neutrals = def_pros_cons_neutrals(dictionnaire)
    trade_offs = def_trade_offs(dictionnaire)
    
    # Si pas assez de trade-offs possibles
    if len(cons) == 0:
        return True, []  # Cas trivial: pas de cons à couvrir
    
    if len(trade_offs) == 0:
        certificat = f"Aucun trade-off valide n'existe. Cons à couvrir: {cons}"
        return False, certificat
    
    try:
        # Créer le modèle Gurobi
        model = gp.Model("Explication_1_1")
        model.setParam('OutputFlag', 0)  # Désactiver l'affichage détaillé
        
        # Variables de décision: z[i] = 1 si le trade-off i est sélectionné
        z = {}
        for i, (pro, con) in enumerate(trade_offs):
            z[i] = model.addVar(vtype=GRB.BINARY, name=f"z_{pro}_{con}")
        
        # Fonction objectif: maximiser le nombre de trade-offs sélectionnés
        model.setObjective(gp.quicksum(z[i] for i in range(len(trade_offs))), GRB.MAXIMIZE)
        
        # Contrainte 1: Chaque con doit être couvert exactement une fois
        for con in cons:
            # Trouver tous les trade-offs qui couvrent ce con
            indices_con = [i for i, (pro, c) in enumerate(trade_offs) if c == con]
            if indices_con:
                model.addConstr(
                    gp.quicksum(z[i] for i in indices_con) == 1,
                    name=f"Couverture_{con}"
                )
            else:
                # Ce con ne peut pas être couvert
                certificat = f"Le critère négatif '{con}' ne peut être couvert par aucun trade-off valide."
                return False, certificat
        
        # Contrainte 2: Chaque pro peut être utilisé au plus une fois
        for pro in pros:
            indices_pro = [i for i, (p, con) in enumerate(trade_offs) if p == pro]
            if indices_pro:
                model.addConstr(
                    gp.quicksum(z[i] for i in indices_pro) <= 1,
                    name=f"Unicite_{pro}"
                )
        
        # Résoudre le problème
        model.optimize()
        
        # Analyser le résultat
        if model.status == GRB.OPTIMAL:
            # Extraire la solution
            explication = []
            for i, (pro, con) in enumerate(trade_offs):
                if z[i].X > 0.5:  # Variable binaire = 1
                    explication.append([pro, con])
            
            # Vérifier que tous les cons sont couverts
            cons_couverts = set(con for pro, con in explication)
            if len(cons_couverts) == len(cons):
                return True, explication
            else:
                cons_non_couverts = set(cons) - cons_couverts
                certificat = f"Impossible de couvrir tous les cons. Cons non couverts: {list(cons_non_couverts)}"
                return False, certificat
        
        elif model.status == GRB.INFEASIBLE:
            # Le problème est infaisable - générer un certificat détaillé
            certificat = "CERTIFICAT DE NON-EXISTENCE:\n"
            certificat += f"  Le modèle est infaisable. Il n'existe pas d'explication 1-1 qui couvre tous les {len(cons)} cons.\n"
            certificat += f"  Raisons possibles:\n"
            certificat += f"    - Pas assez de pros disponibles ({len(pros)} pros pour {len(cons)} cons)\n"
            certificat += f"    - Certains cons ne peuvent être compensés par aucun pro\n"
            
            # Calculer IIS (Irreducible Inconsistent Subsystem) pour identifier les contraintes en conflit
            try:
                model.computeIIS()
                certificat += f"    - Contraintes en conflit identifiées par Gurobi:\n"
                for c in model.getConstrs():
                    if c.IISConstr:
                        certificat += f"      * {c.ConstrName}\n"
            except:
                pass
            
            return False, certificat
        
        else:
            certificat = f"Le solveur n'a pas trouvé de solution. Statut Gurobi: {model.status}"
            return False, certificat
    
    except gp.GurobiError as e:
        return False, f"Erreur Gurobi: {str(e)}"

def exist_explication_1_1(dictionnaire): 
    """Version originale (heuristique gloutonne) - conservée pour comparaison."""
    _,cons,_ = def_pros_cons_neutrals(dictionnaire)
    trade_offs = def_trade_offs(dictionnaire)
    union_con = []
    index_con = []
    explication = []
    for i in range(len(trade_offs)):
        if trade_offs[i][1] not in union_con:
            union_con.append(trade_offs[i][1])
            index_con.append(i)
    
    if len(union_con) < len(cons):
        return False, explication
    else:
        explication = [trade_offs[i] for i in index_con]
        return True, explication
        

if __name__ == "__main__":
    print("="*60)
    print("ANALYSE DES TRADE-OFFS")
    print("="*60)
    
    # Afficher le dictionnaire des cours
    print("\nDictionnaire des cours (x - y):")
    for cours, valeur in Dictionnaire_cours.items():
        print(f"  {cours}: {valeur:+d}")
    
    # Identifier pros et cons
    pros, cons, neutrals = def_pros_cons_neutrals(Dictionnaire_cours)
    print(f"\nPros (critères positifs): {pros}")
    print(f"Cons (critères négatifs): {cons}")
    if neutrals:
        print(f"Neutres: {neutrals}")
    
    # Calculer tous les trade-offs possibles
    trade_offs = def_trade_offs(Dictionnaire_cours)
    print(f"\nTrade-offs valides trouvés: {len(trade_offs)}")
    for trade_off in trade_offs:
        pro, con = trade_off
        somme = Dictionnaire_cours[pro] + Dictionnaire_cours[con]
        print(f"  [{pro}, {con}] -> {Dictionnaire_cours[pro]} + ({Dictionnaire_cours[con]}) = {somme}")
    
    print("\n" + "="*60)
    print("MÉTHODE AVEC SOLVEUR D'OPTIMISATION (GUROBI)")
    print("="*60)
    
    # Utiliser le solveur d'optimisation
    exist_solveur, resultat_solveur = exist_explication_1_1_avec_solveur(Dictionnaire_cours)
    
    print(f"\nExistence d'une explication 1-1: {exist_solveur}")
    if exist_solveur:
        print("✓ EXPLICATION TROUVÉE:")
        print(f"  Nombre de trade-offs: {len(resultat_solveur)}")
        for pro, con in resultat_solveur:
            somme = Dictionnaire_cours[pro] + Dictionnaire_cours[con]
            print(f"  - [{pro}, {con}] : {Dictionnaire_cours[pro]} + ({Dictionnaire_cours[con]}) = {somme}")
        
        # Vérifier la couverture
        cons_couverts = set(con for pro, con in resultat_solveur)
        print(f"\n  Cons couverts: {sorted(cons_couverts)}")
        print(f"  Tous les cons sont couverts: {cons_couverts == set(cons)}")
    else:
        print("✗ CERTIFICAT DE NON-EXISTENCE:")
        print(f"  {resultat_solveur}")
    
    print("\n" + "="*60)
    print("COMPARAISON: MÉTHODE HEURISTIQUE (ORIGINALE)")
    print("="*60)
    
    # Comparer avec la méthode heuristique originale
    exist_heuristique, explication_heuristique = exist_explication_1_1(Dictionnaire_cours)
    print(f"\nExistence d'une explication 1-1: {exist_heuristique}")
    if exist_heuristique:
        print("Explication 1-1 (heuristique):")
        for trade_off in explication_heuristique:
            print(f"  {trade_off}")