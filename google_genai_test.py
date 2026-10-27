
import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
print("model_used " , model)

if not api_key:
    raise SystemExit("ERROR: GEMINI_API_KEY is missing from your .env file.")

citation = r"""\bibitem{Kunz2014} Kunz M W, Schekochihin A A and Stone J M 2014 \textit{Phys. Rev. Lett.} \href{https\://doi.org/10.1103/PhysRevLett.112.205003}{\textbf{112} 205003}."""

prompt = f"""
Convert the following LaTeX bibliography reference into the specified
Vancouver-style journal reference format.

INPUT:
{citation}

REQUIRED STYLE EXAMPLE:
\\bibitem{{Ghosh2017}} Ghosh S, Chattopadhyay PK, Ghosh J, Pal R, Bora D. \\\\
Transition from single to multiple axial potential structure in expanding
helicon plasma. J Phys D Appl Phys. 2017;50(6):065201.
doi:10.1088/1361-6463/aa5068.

RULES:
1. Preserve the original citation key inside \\bibitem{{...}}.
2. Format authors as Surname Initials, without spaces between initials.
3. Separate authors with commas and put a period after the author list.
4. Put the article title in sentence case after the authors.
5. Use the abbreviated journal name.
6. Format publication details as Year;Volume(Issue):Pages or article number.
7. End with doi:DOI_VALUE.
8. Remove unnecessary LaTeX formatting commands such as \\textit,
   \\textbf, and \\href from the final rendered reference.
9. Do not invent missing metadata. If the title or issue number is
   unavailable in the input, use DOI metadata lookup if available.
   Otherwise, format the available information without guessing.
10. Return ONLY the converted reference, with no explanation,
    Markdown code fences, or introductory text.

Convert this reference now.
"""

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    result = (response.text or "").strip()

    if result:
        print("\nCONVERTED CITATION:\n")
        print(result)
    else:
        print("ERROR: Gemini returned an empty response.")

except errors.APIError as exc:
    print("FAILED: Gemini API request failed.")
    print(f"Status code: {exc.code}")
    print(f"Details: {exc.message}")

except Exception as exc:
    print(f"ERROR: {type(exc).__name__}: {exc}")
