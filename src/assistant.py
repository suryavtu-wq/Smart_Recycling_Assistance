import os
from .recommendations import GUIDANCE

def answer_question(question):
    """
    Safe offline fallback. This does NOT claim to be Llama.
    Configure the ExecuTorch Llama runner separately; see executorch_llama/README.md.
    """
    q = question.lower()
    for category, guide in GUIDANCE.items():
        if category.lower() in q:
            return (
                f"**{category}**\n\n"
                f"**Disposal:** {guide['disposal']}\n\n"
                f"**Recycling:** {guide['recycling']}\n\n"
                f"**Environmental note:** {guide['impact']}"
            ), "Local recycling knowledge base (Llama not configured)"
    keywords = {
        "segregat": "Separate wet/organic waste, dry recyclable materials, and residual waste. Follow your local municipality's collection categories.",
        "compost": "Compost suitable food scraps and garden waste using an appropriate, well-managed composting method.",
        "battery": "Do not put batteries in ordinary mixed waste. Use an authorised battery or e-waste collection point.",
        "electronic": "Keep electronic waste separate and use an authorised e-waste collection or take-back facility.",
        "plastic": GUIDANCE["Plastic"]["disposal"] + " " + GUIDANCE["Plastic"]["recycling"],
        "glass": GUIDANCE["Glass"]["disposal"],
        "paper": GUIDANCE["Paper"]["disposal"],
    }
    for key, value in keywords.items():
        if key in q:
            return value, "Local recycling knowledge base (Llama not configured)"
    return (
        "I can help with waste segregation, recycling, composting, and disposal. "
        "Mention the material (for example, plastic, glass, paper, metal, food waste, or textiles). "
        "For hazardous items such as batteries and e-waste, use an authorised collection facility."
    ), "Local recycling knowledge base (Llama not configured)"
