#!/usr/bin/env python3
from pathlib import Path

out = Path(__file__).with_name("proof.svg")
svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"320\" height=\"180\"><rect width=\"320\" height=\"180\" fill=\"#111\"/><rect x=\"188\" y=\"20\" width=\"108\" height=\"140\" rx=\"12\" fill=\"#d8d8d8\"/><text x=\"24\" y=\"76\" font-family=\"sans-serif\" font-size=\"19\" font-weight=\"700\" fill=\"white\">Synthetic</text><text x=\"24\" y=\"102\" font-family=\"sans-serif\" font-size=\"19\" font-weight=\"700\" fill=\"white\">proof style</text><text x=\"24\" y=\"130\" font-family=\"sans-serif\" font-size=\"10\" fill=\"#aaa\">executable proof</text></svg>\n"""
out.write_text(svg, encoding="utf-8")
print(out)
