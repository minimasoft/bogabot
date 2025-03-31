#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
from pathlib import Path
import json
import markdown
import sys
from global_config import gconf
from file_db import FileDB
from datetime import date, timedelta,datetime
from csv import DictWriter

public_path = Path('../public/')
public_path.mkdir(exist_ok=True)


norm_meta = gconf("NORM_META")
db = FileDB(
    gconf("FILEDB_PATH"),
    gconf("FILEDB_SALT"),
)
today = date.today() + timedelta(days=1)
curr_date = date(2025,1,2)
# Danger load:
all_norms = list(db.all(norm_meta))
all_days = []
while(curr_date <= today):
    day = curr_date.day
    month = curr_date.month
    year = curr_date.year

    html_path = public_path / f"bo{year-2000}{month:02}{day:02}.html"
    json_path = public_path / f"bo{year-2000}{month:02}{day:02}.personal.json"
    csv_path = public_path / f"bo{year-2000}{month:02}{day:02}.designa.csv"
    target_date = f"{year}-{month:02}-{day:02}"
    print(f"Checking data for: {target_date}")

    results = [
        norm
        for norm in all_norms
        if 'publish_date' in norm and norm['publish_date'] == target_date
    ]

    if len(results) > 0:
        skip_write = False
        if html_path.exists() == True:
            html_time = html_path.stat().st_ctime
            result_time = max(map(lambda r: r.e()['time'], results)) + 1
            if result_time < html_time:
                print(f"Skip write, already up to date")
                skip_write = True
        if skip_write == False:
            print(f"Writing {len(results)} norms...")
            with open(html_path, 'w') as html_o:
                html_o.write("""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
@font-face {
font-family: 'Noto Sans Mono';
font-style: normal;
font-weight: 400;
font-stretch: 100%;
src: url(/NotoSansMonoLatin.woff2) format('woff2');
unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}

body {
    font-family: 'Noto Sans Mono';
    font-size: 16px;
}

table {
border: 1px solid black;
border-collapse: collapse;
width: 100%;
max-width: 1000px;
}

td {
border: 1px solid black;
border-collapse: collapse;
vertical-align: top;
text-align: left;
padding: 10px;
}

.details_1 > summary {
list-style: none;
}

.details_1 > summary::-webkit-details-marker {
display: none;
}

.svg_icon {
    color: #222222;
}

.json_data {
overflow: scroll;
max-width: 1000px;
}

</style>
</head>
<body>
<table>
<tbody>
<tr><td>
<a href='/bora/'><img src=bogabanner.png></img></a>
</td></tr>
<tr><td>
<h2>Agregado de la sección primera del bolet&iacute;n oficial fecha """)
                html_o.write(f"{day}/{month}/{year}</h2></td></tr>")
                appoint_list = []
                resign_list = []
                for result in sorted(results, key=lambda r: r['ext_id']):
                    if 'appoint_list' in result:
                        for appointment in result['appoint_list']:
                            appointment['via'] = result['data_link']
                            appointment['norm_official_id'] = result['official_id']
                            appointment['norm_publish_date'] = result['publish_date']
                            appoint_list.append(appointment)
                    if 'resign_list' in result:
                        for resign in result['resign_list']:
                            resign['via'] = result['data_link']
                            resign_list.append(resign)
                    html_o.write(f"<tr>\n<td><div id='bo{result['ext_id']}' class='")
                    if 'tags' in result:
                        html_o.write(" ".join(tag[1:] for tag in result['tags']))
                    html_o.write("'>\n")
                    html_o.write(f"<details open class=details_1><summary><a href=#bo{result['ext_id']}><img class=svg_icon src='svg/l.svg'></a> <b>{result['subject']}  -  {result['official_id'] or result['name']}</b><br>")
                    if 'tags' in result:
                        html_o.write(f"{' '.join(result['tags'])}")
                    else:
                        html_o.write("procesando tags...")
                    html_o.write(f"</summary><hr>via: <a href={result['data_link']}>{result['data_link']}</a>\n")
                    if 'brief' in result:
                        brief = result['brief']
                        brief = markdown.markdown(brief)        
                        html_o.write(f"<p>{brief}</p>\n")
                    else:
                        html_o.write(f"<p>procesando resumen de bogabot...</p>")
                    if 'ref' in result and result['ref'] is not None:
                        ref = result['ref']
                        ref = markdown.markdown(ref)        
                        html_o.write(f"<details><summary><b>Referencias</b></summary>{ref}</details>\n")

                    refs = ""
                    if 'law_ref' in result and len(result['law_ref']) > 0:
                        refs += f"<li>Leyes:<ul>\n"
                        for ref in result['law_ref']:
                            refs += f"<li>{ref['ref']}"
                            if 'infolegs' in ref:
                                for infoleg in ref['infolegs']:
                                    refs += f"<br>infoleg <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={infoleg}>{infoleg}</a>\n"
                            refs += "</li>\n"
                        refs += "</ul></li>\n"

                    if 'decree_ref' in result and len(result['decree_ref']) > 0:
                        refs += f"<li>Decretos:<ul>\n"
                        for ref in result['decree_ref']:
                            if 'ref' in ref:
                                refs += f"<li>{ref['ref']}"
                                if 'infolegs' in ref:
                                    for infoleg in ref['infolegs']:
                                        refs += f"<br>infoleg <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={infoleg}>{infoleg}</a>\n"
                                refs += "</li>\n"
                        refs += "</ul></li>\n"
                    if refs != "":
                        refs = f"<ul>{refs}</ul>"
                        html_o.write(f"<details><summary><b><u>Referencias</u></b></summary>{refs}</details>\n")
                        

                    if 'analysis' in result and result['analysis'] is not None:
                        analysis = result['analysis']
                        analysis = markdown.markdown(analysis)        
                        html_o.write(f"<details><summary><b><u>Análisis de bogabot</u></b></summary>{analysis}</details>\n")
                    html_o.write(f"<details><summary><b><u>Ver texto original</u></b></summary>{result['full_text']}</details>\n")
                    html_o.write(f"</details>\n</div>\n</td>\n</tr>\n")
                html_o.write(f"<tr><td><div id=bonus_1 class=json_data><h2><a href='bo{year-2000}{month:02}{day:02}.personal.json'> Bonus 1: JSON designaciones y renuncias</a></h2><hr></div></td></tr>\n")
                html_o.write(f"<tr><td><div id=bonus_2 class=json_data><h2><a href='bo{year-2000}{month:02}{day:02}.designa.csv'>Bonus 2: CSV designaciones</a></h2><hr></div></td></tr>\n")
                html_o.write('\n</tbody></table></body></html>\n')
                with open(json_path, 'wt', encoding='utf-8') as jf:
                    json.dump({
                        'in': appoint_list,
                        'out': resign_list,
                    },jf,ensure_ascii=False,indent=2)
                attrs = list("norm_publish_date,name,gov_id,gov_section,position,position_start,position_duration_days,norm_official_id,norm_link".split(","))
                with open(csv_path,'w',encoding='utf-8') as csv_f:
                    writer = DictWriter(csv_f, fieldnames=attrs, dialect='excel')
                    writer.writeheader()
                    for appoint in appoint_list:
                        appoint['norm_link'] = f'=HYPERLINK("{appoint["via"]}")'
                        appoint.pop('via')
                        writer.writerow(appoint)
    if html_path.exists() == True:
        all_days.append(target_date)
    curr_date = curr_date + timedelta(days=1)
with open(public_path / "index.html", "w", encoding="utf-8") as html_i:
    html_i.write("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
</head>
<body>
<h2>Experimento bogabot</h2>
(el m&aacute;s reciente primero)
<h3><ul>
""")
    for day in reversed(all_days):
        year = day[2:4]
        month = day[5:7]
        day = day[8:10]
        html_i.write(f"    <li><a href=bo{year+month+day}.html>Boletín oficial del {day}/{month}/{year}</a></li>\n")
    html_i.write("""</ul></h3>
</body>
</html>
""")
