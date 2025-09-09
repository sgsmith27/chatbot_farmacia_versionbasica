from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

SINTOMA_RECOMENDACION: Dict[str, Dict[str, str]] = {
    "dolor de cabeza": {
        "medicamento": "paracetamol",
        "forma": "tabletas 500 mg",
        "dosis": "500–1000 mg cada 6–8 h (máx. 3–4 g/día)",
        "consejos": "hidratarse, descanso",
    },
    "fiebre": {
        "medicamento": "paracetamol",
        "forma": "tabletas 500 mg",
        "dosis": "500–1000 mg cada 6–8 h (máx. 3–4 g/día)",
        "consejos": "bebidas frías, vigilar temperatura",
    },
    "diarrea": {
        "medicamento": "loperamida",
        "forma": "tabletas 2 mg",
        "dosis": "2 mg tras cada deposición (máx. 8 mg/día)",
        "consejos": "soluciones de rehidratación oral",
    },
    "tos": {
        "medicamento": "dextrometorfano",
        "forma": "jarabe",
        "dosis": "según etiqueta (adultos: 10–20 mg c/4–6 h)",
        "consejos": "miel/limón, evitar irritantes",
    },
    "acidez estomacal": {
        "medicamento": "omeprazol",
        "forma": "cápsulas 20 mg",
        "dosis": "20 mg una vez al día (antes del desayuno)",
        "consejos": "evitar comidas copiosas/grasas",
    },
}

FARMACOS: Dict[str, Dict[str, str]] = {
    "paracetamol": {
        "descripcion": "Analgésico y antipirético.",
        "presentacion": "Tabletas 500–1000 mg; suspensión.",
        "uso": "Dolor leve-moderado, fiebre.",
        "dosis": "Adultos: 500–1000 mg c/6–8 h (máx. 3–4 g/día).",
        "efectos": "Náuseas (raro: hepatotoxicidad por sobredosis).",
        "advertencias": "No exceder dosis máxima; precaución hepática.",
    },
    "ibuprofeno": {
        "descripcion": "AINE analgésico/antiinflamatorio.",
        "presentacion": "Tabletas/cápsulas 200–400 mg.",
        "uso": "Dolor musculoesquelético, cefalea, dismenorrea, fiebre.",
        "dosis": "200–400 mg c/6–8 h (máx. 1200 mg/día OTC).",
        "efectos": "Molestias gástricas, mareo.",
        "advertencias": "Evitar en úlcera o insuficiencia renal.",
    },
    "loperamida": {
        "descripcion": "Antidiarreico que reduce motilidad intestinal.",
        "presentacion": "Tabletas 2 mg.",
        "uso": "Diarrea aguda no complicada.",
        "dosis": "2 mg tras cada deposición (máx. 8 mg/día).",
        "efectos": "Estreñimiento, cólicos.",
        "advertencias": "Hidratación adecuada; no usar en diarrea con sangre/fiebre alta.",
    },
    "dextrometorfano": {
        "descripcion": "Antitusivo para tos seca irritativa.",
        "presentacion": "Jarabe/cápsulas.",
        "uso": "Tos seca.",
        "dosis": "Adultos: 10–20 mg c/4–6 h (según etiqueta).",
        "efectos": "Somnolencia leve, mareo.",
        "advertencias": "Evitar combinar con alcohol; consultar si tos > 1 semana.",
    },
    "omeprazol": {
        "descripcion": "IBP que reduce el ácido gástrico.",
        "presentacion": "Cápsulas 20 mg.",
        "uso": "Acidez/ERGE.",
        "dosis": "20 mg antes del desayuno.",
        "efectos": "Dolor de cabeza, molestias GI.",
        "advertencias": "Uso prolongado bajo control médico.",
    },
}


def norm(txt: str) -> str:
    return (txt or "").strip().lower()

def titulo(txt: str) -> str:
    return txt[:1].upper() + txt[1:] if txt else txt

def sugerencias_simples(valor: str, candidatos: List[str], n: int = 3) -> List[str]:
    """Sugerencias muy básicas por prefijo/substring (sin fuzzy lib)."""
    v = norm(valor)
    hits = [c for c in candidatos if v in c]
    if not hits:
        hits = [c for c in candidatos if c.startswith(v[:3])]
    return hits[:n]


class ActionElegirOpcion(Action):
    def name(self) -> Text:
        return "action_elegir_opcion"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        txt = norm(tracker.latest_message.get("text", ""))
        if txt in {"1", "consultar síntoma", "consultar sintoma", "consultar por síntoma", "consultar por sintoma", "síntomas", "sintomas"}:
            dispatcher.utter_message(response="utter_solicitar_sintoma")
        elif txt in {"2", "consultar medicamento", "consultar por nombre", "medicamentos"}:
            dispatcher.utter_message(response="utter_pedir_medicamento")
        else:
            dispatcher.utter_message(response="utter_menu")
        return []

class ActionConsultarSintoma(Action):
    def name(self) -> Text:
        return "action_consultar_sintoma"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ent = next((e for e in tracker.latest_message.get("entities", []) if e.get("entity") == "sintoma"), None)
        texto = ent.get("value") if ent else tracker.latest_message.get("text", "")
        s = norm(texto)

        
        keys = list(SINTOMA_RECOMENDACION.keys())
        if s in SINTOMA_RECOMENDACION:
            info = SINTOMA_RECOMENDACION[s]
        else:
            
            match = next((k for k in keys if s in k or k in s), None)
            if match:
                info = SINTOMA_RECOMENDACION[match]
                s = match
            else:
                sugeridos = sugerencias_simples(s, keys)
                if sugeridos:
                    dispatcher.utter_message(
                        text=f"No identifiqué el síntoma con certeza. ¿Quisiste decir: {', '.join(sugeridos)}?\nTambién puedes pedir *lista de síntomas*."
                    )
                else:
                    dispatcher.utter_message(text="No reconozco ese síntoma. Puedes pedir *lista de síntomas*.")
                return []

        msg = (
            f"🩺 *Recomendación para {titulo(s)}*\n"
            f"• Medicamento: {info['medicamento']}\n"
            f"• Forma: {info['forma']}\n"
            f"• Dosis: {info['dosis']}\n"
            f"• Consejos: {info['consejos']}"
        )
        dispatcher.utter_message(text=msg)
        return []

class ActionConsultarPorNombre(Action):
    def name(self) -> Text:
        return "action_consultar_por_nombre"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        ent = next((e for e in tracker.latest_message.get("entities", []) if e.get("entity") == "medicamento"), None)
        texto = ent.get("value") if ent else tracker.latest_message.get("text", "")
        m = norm(texto)

        keys = list(FARMACOS.keys())
        if m in FARMACOS:
            info = FARMACOS[m]
        else:
            match = next((k for k in keys if m in k or k in m), None)
            if match:
                info = FARMACOS[match]
                m = match
            else:
                sugeridos = sugerencias_simples(m, keys)
                if sugeridos:
                    dispatcher.utter_message(
                        text=f"No encontré “{texto}”. ¿Te refieres a: {', '.join(sugeridos)}?\nTambién puedes pedir *lista de medicamentos*."
                    )
                else:
                    dispatcher.utter_message(text="No reconozco ese medicamento. Puedes pedir *lista de medicamentos*.")
                return []

        msg = (
            f"💊 *{titulo(m)}*\n"
            f"• Descripción: {info['descripcion']}\n"
            f"• Presentación: {info['presentacion']}\n"
            f"• Uso recomendado: {info['uso']}\n"
            f"• Dosis (orientativa): {info['dosis']}\n"
            f"• Efectos secundarios: {info['efectos']}\n"
            f"• Advertencias: {info['advertencias']}"
        )
        dispatcher.utter_message(text=msg)
        return []

class ActionListarSintomas(Action):
    def name(self) -> Text:
        return "action_listar_sintomas"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        lista = "\n".join([f"• {titulo(k)}" for k in SINTOMA_RECOMENDACION.keys()])
        dispatcher.utter_message(text=f"📋 *Síntomas disponibles*\n{lista}\n\nEscribe uno para consultar.")
        return []

class ActionListarMedicamentos(Action):
    def name(self) -> Text:
        return "action_listar_medicamentos"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        lista = "\n".join([f"• {titulo(k)}" for k in FARMACOS.keys()])
        dispatcher.utter_message(text=f"📋 *Medicamentos disponibles*\n{lista}\n\nEscribe uno para consultar.")
        return []
