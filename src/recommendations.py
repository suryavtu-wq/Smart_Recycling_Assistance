GUIDANCE = {
    "Cardboard": {
        "disposal": "Keep cardboard dry and clean. Flatten boxes and place them in the paper/cardboard recycling stream where accepted. Remove excessive tape and plastic wrapping.",
        "recycling": "Clean cardboard can be pulped and made into new paper products and packaging.",
        "impact": "Recovering cardboard reduces demand for virgin paper fibre and diverts bulky material from disposal."
    },
    "Food Organics": {
        "disposal": "Separate food scraps from dry recyclables. Use a municipal organic-waste collection service or a suitable composting system if available.",
        "recycling": "Food scraps can be composted or processed through approved anaerobic digestion facilities.",
        "impact": "Separating organics can reduce landfill methane generation and return nutrients to soil when properly processed."
    },
    "Glass": {
        "disposal": "Keep glass separate and follow local rules. Do not place broken glass loose in a bag; wrap it securely and label it to prevent injuries.",
        "recycling": "Accepted glass containers can be sorted, crushed into cullet, and remelted into new glass products.",
        "impact": "Glass recycling can reduce raw-material extraction and energy use in glass manufacturing."
    },
    "Metal": {
        "disposal": "Keep metal items separate from wet waste. Empty containers and check local collection rules. Handle sharp edges carefully.",
        "recycling": "Many steel and aluminium items can be sorted, melted, and made into new metal products.",
        "impact": "Metal recovery conserves finite resources and can save substantial energy compared with primary production."
    },
    "Miscellaneous Trash": {
        "disposal": "This category is mixed or not clearly recyclable. Check whether the item can be separated into material types. Use residual-waste collection only after checking local options.",
        "recycling": "Some items may be recoverable through specialist facilities, but this category cannot be assigned one universal recycling route.",
        "impact": "Correct identification and separation can prevent recoverable materials from entering residual waste."
    },
    "Paper": {
        "disposal": "Keep paper clean and dry. Separate it from food-contaminated or laminated materials unless your local programme accepts them.",
        "recycling": "Accepted paper can be pulped, cleaned, and converted into new paper products.",
        "impact": "Paper recovery can reduce demand for virgin fibre and lower the volume of waste sent to landfill."
    },
    "Plastic": {
        "disposal": "Check the resin type and local collection rules. Empty and rinse containers when required. Do not assume every plastic item is accepted in curbside recycling.",
        "recycling": "Some plastics can be mechanically recycled into flakes or pellets. Flexible, multilayer, and contaminated plastics may need specialist collection or may not be recyclable locally.",
        "impact": "Correct sorting improves material recovery and reduces plastic leakage into the environment."
    },
    "Textile Trash": {
        "disposal": "If clean and usable, consider donation or textile take-back programmes. Wet, mouldy, or heavily contaminated textiles may not be accepted.",
        "recycling": "Some textiles can be reused, mechanically fibre-recycled, or processed by specialist textile recovery facilities.",
        "impact": "Reuse and textile recovery can reduce demand for new fibres and lower textile waste."
    },
    "Vegetation": {
        "disposal": "Keep garden waste separate from general rubbish. Follow local green-waste collection or composting guidance.",
        "recycling": "Leaves, grass, and small plant trimmings can often be composted or chipped for mulch.",
        "impact": "Composting vegetation returns organic matter to soil and reduces disposal volumes."
    }
}

def get_guidance(category):
    return GUIDANCE.get(category, {
        "disposal": "Check local municipal waste guidance before disposal.",
        "recycling": "Recycling options depend on the exact material and local facilities.",
        "impact": "Correct segregation supports resource recovery."
    })
