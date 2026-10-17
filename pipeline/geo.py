"""Country and city normalization for public DACH job boards."""
import re
import unicodedata


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)).casefold() if not unicodedata.combining(c)).replace('ß', 'ss').strip()

COUNTRY = {key(v): code for code, names in [('DE', 'DE|DEU|Germany|Deutschland'), ('AT', 'AT|AUT|Austria|Österreich'), ('CH', 'CH|CHE|Switzerland|Schweiz|Suisse|Svizzera')] for v in names.split('|')}
CITY = {}
_GROUPS = {
'Bayern': 'München|Munich|Nürnberg|Nuremberg|Fürth|Erlangen|Garching|Ismaning|Unterföhring|Herzogenaurach|Ingolstadt|Augsburg|Regensburg|Würzburg|Bamberg|Bayreuth|Passau|Landshut|Rosenheim|Kempten|Schweinfurt|Aschaffenburg|Neu-Ulm|Freising|Dachau|Starnberg|Ottobrunn|Neubiberg|Unterschleißheim|Germering|Kaufbeuren|Hof|Coburg|Straubing|Amberg|Weiden|Memmingen|Ansbach|Schwabach|Erding|Deggendorf',
'Baden-Württemberg': 'Stuttgart|Karlsruhe|Mannheim|Freiburg|Freiburg im Breisgau|Heidelberg|Heilbronn|Ulm|Pforzheim|Reutlingen|Esslingen|Ludwigsburg|Tübingen|Konstanz|Villingen-Schwenningen|Aalen|Sindelfingen|Böblingen|Friedrichshafen|Offenburg|Göppingen|Baden-Baden|Waiblingen|Ravensburg|Schwäbisch Gmünd|Schwäbisch Hall|Walldorf|Weinheim|Bruchsal|Singen|Bietigheim-Bissingen|Leonberg|Leinfelden-Echterdingen|Filderstadt|Ettlingen|Backnang|Biberach|Neckarsulm|Rottweil|Tuttlingen',
'Nordrhein-Westfalen': 'Köln|Cologne|Düsseldorf|Dortmund|Essen|Duisburg|Bochum|Wuppertal|Bielefeld|Bonn|Münster|Gelsenkirchen|Mönchengladbach|Aachen|Krefeld|Oberhausen|Hagen|Hamm|Mülheim|Mülheim an der Ruhr|Leverkusen|Solingen|Herne|Neuss|Paderborn|Bottrop|Bergisch Gladbach|Remscheid|Recklinghausen|Moers|Siegen|Gütersloh|Witten|Iserlohn|Düren|Ratingen|Lünen|Marl|Velbert|Minden|Viersen|Rheine|Detmold|Arnsberg|Lippstadt|Lüdenscheid|Herford|Hürth|Kerpen|Dormagen|Grevenbroich|Wesel|Bergheim|Euskirchen|Sankt Augustin|Hilden|Langenfeld|Jülich|Monheim|Gummersbach',
'Hessen': 'Frankfurt|Frankfurt am Main|Wiesbaden|Kassel|Darmstadt|Offenbach|Offenbach am Main|Hanau|Gießen|Marburg|Fulda|Rüsselsheim|Bad Homburg|Wetzlar|Oberursel|Dreieich|Neu-Isenburg|Eschborn|Bensheim|Friedberg|Bad Vilbel|Langen',
'Niedersachsen': 'Hannover|Hanover|Braunschweig|Oldenburg|Osnabrück|Wolfsburg|Göttingen|Salzgitter|Hildesheim|Delmenhorst|Wilhelmshaven|Lüneburg|Celle|Garbsen|Hameln|Lingen|Nordhorn|Wolfenbüttel|Goslar|Emden|Cuxhaven|Stade|Gifhorn|Peine|Laatzen',
'Rheinland-Pfalz': 'Mainz|Ludwigshafen|Ludwigshafen am Rhein|Koblenz|Trier|Kaiserslautern|Worms|Neuwied|Neustadt|Speyer|Landau|Frankenthal|Bad Kreuznach|Pirmasens|Ingelheim',
'Sachsen': 'Leipzig|Dresden|Chemnitz|Zwickau|Plauen|Görlitz|Freiberg|Bautzen|Radebeul|Pirna',
'Sachsen-Anhalt': 'Halle|Halle (Saale)|Magdeburg|Dessau|Dessau-Roßlau|Wittenberg|Bitterfeld|Merseburg|Halberstadt',
'Thüringen': 'Erfurt|Jena|Ilmenau|Gera|Weimar|Gotha|Eisenach|Nordhausen|Suhl',
'Brandenburg': 'Potsdam|Cottbus|Brandenburg an der Havel|Frankfurt (Oder)|Oranienburg|Falkensee|Bernau|Wildau|Teltow',
'Mecklenburg-Vorpommern': 'Rostock|Schwerin|Neubrandenburg|Stralsund|Greifswald|Wismar',
'Schleswig-Holstein': 'Kiel|Lübeck|Flensburg|Neumünster|Norderstedt|Elmshorn|Pinneberg|Wedel',
'Saarland': 'Saarbrücken|Neunkirchen|Homburg|Sankt Ingbert|Saarlouis',
'Berlin': 'Berlin', 'Hamburg': 'Hamburg', 'Bremen': 'Bremen|Bremerhaven',
'Österreich': 'Wien|Vienna|Graz|Linz|Salzburg|Innsbruck|Klagenfurt|Villach|Wels|Sankt Pölten|Dornbirn|Wiener Neustadt|Steyr|Feldkirch|Bregenz|Leoben|Kapfenberg|Hagenberg|Kufstein',
'Schweiz': 'Zürich|Zurich|Bern|Basel|Lausanne|Genf|Geneva|Luzern|Lucerne|Winterthur|Sankt Gallen|St. Gallen|Lugano|Biel|Zug|Schaffhausen|Thun|Chur|Freiburg im Üechtland|Neuenburg|Neuchâtel|Baden|Dübendorf|Dietikon|Rapperswil|Rotkreuz|Uster|Olten'
}
for region, cities in _GROUPS.items():
    for city in cities.split('|'):
        CITY[key(city)] = ('AT' if region == 'Österreich' else 'CH' if region == 'Schweiz' else 'DE', region)
US_STATES = r'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|USA|U\.S\.|Canada|Australia|India|Brazil|Mexico|China|Japan|Korea|Philippines|Vietnam|South Africa|Nigeria|Kenya|Egypt|Argentina|Colombia|Chile|Peru|Indonesia|Malaysia|Thailand|Pakistan|Bangladesh|Ukraine|Serbia|Croatia|Slovenia|Slovakia|Hungary|Romania|Bulgaria|Greece|Turkey|Türkei|Ireland|Irland|Scotland|Belgium|Belgien|Luxembourg|Luxemburg|Denmark|Dänemark|Sweden|Schweden|Norway|Norwegen|Finland|Finnland|Estonia|Latvia|Lithuania|Cyprus|Malta|Israel|Saudi|Qatar|Emirates|Birmingham|Manchester|Dublin|Brussels|Brüssel|Copenhagen|Stockholm|Oslo|Helsinki|Tallinn|Riga|Vilnius|Budapest|Bratislava|Ljubljana|Zagreb|Belgrade|Athens|Valencia|Porto|Lyon|Rotterdam|Utrecht|Eindhoven|Antwerp|Gdansk|Wroclaw|Poznan|Brno|Bangalore|Bengaluru|Mumbai|Delhi|Hyderabad|Pune|Chennai|Sydney|Melbourne|Boston|Chicago|Austin|Seattle|Denver|Atlanta|Miami|Dallas|Houston|Los Angeles|Vancouver|Montreal|Mexico City|São Paulo|Sao Paulo|Buenos Aires|Bogotá|Bogota|Cape Town|Lagos|Nairobi|Cairo|Tokyo|Seoul|Shanghai|Beijing|Shenzhen|Hong Kong|Taipei|Manila|Jakarta|Kuala Lumpur|Bangkok|Ho Chi Minh|Hanoi'
FOREIGN = re.compile(r'\b(?:' + US_STATES + r')\b|\b[A-Z][a-z]+,\s*(?:AL|AK|AZ|AR|CA|CO|CT|FL|GA|IL|IN|MA|MD|MI|MN|NC|NJ|NY|OH|OR|PA|TN|TX|UT|VA|WA|WI)\b')
NON_DACH = re.compile(r'\b(?:' + US_STATES + r')\b|\b(?:[A-Z][a-z]+,\s*(?:AL|AK|AZ|AR|CA|CO|CT|FL|GA|IL|IN|MA|MD|MI|MN|NC|NJ|NY|OH|OR|PA|TN|TX|UT|VA|WA|WI)\b)|' + r'London|Paris|Lisbon|Lisboa|Barcelona|Madrid|Amsterdam|Warsaw|Warszawa|Krakow|Kraków|Prague|Praha|Milan|Milano|New York|San Francisco|Toronto|Sofia|Bucharest|Kyiv|Istanbul|Dubai|Singapore|Tel Aviv|United Kingdom|United States|France|Spain|Portugal|Poland|Netherlands|Italy|India|China|Bangalore|Bengaluru|Dublin|Stockholm|Copenhagen|Helsinki|Oslo|Budapest|Brussels|Bruxelles|Macedonia|Skopje|Serbia|Belgrade|Beograd|Romania|Cluj|Iasi|Croatia|Zagreb|Greece|Athens|Turkey|Türkei|Ukraine|Lviv|Canada|Montreal|Vancouver|USA|United Arab Emirates|Abu Dhabi|Porto|Valencia|Sevilla|Malaga|Málaga|Bulgaria|Hungary|Czech|Brno|Slovakia|Bratislava|Slovenia|Ljubljana|Bosnia|Sarajevo|Albania|Tirana|Kosovo|Pristina|Lithuania|Vilnius|Latvia|Riga|Estonia|Tallinn|Finland|Sweden|Norway|Denmark|Belgium|Luxembourg|Ireland|Philippines|Manila|Brazil|Mexico|Argentina|Egypt|Cairo|Morocco|Tunisia|Pakistan|Vietnam|Japan|Tokyo|Australia|Sydney|Rotterdam|Utrecht|Eindhoven|Lyon|Toulouse|Wroclaw|Wrocław|Gdansk|Poznan|Łódź|Lodz|Belgrad|Novi Sad|Timisoara|Chennai|Pune|Hyderabad|Mumbai|Delhi|Seoul|Shanghai|Beijing|Shenzhen|Taipei|Boston|Seattle|Austin|Chicago|Los Angeles|Sunnyvale|Palo Alto|Mountain View|Atlanta|Denver|Miami|Washington|^(?!DEU|AUT|CHE)[A-Z]{3}\s*[-–_]', re.I)
NON_DACH = re.compile(r'(?<![\wÄÖÜäöüß])(?:' + NON_DACH.pattern + r')(?![\wÄÖÜäöüß])', NON_DACH.flags & ~re.UNICODE)  # nur ganze Wörter (Rigaer Straße ≠ Riga)


STATES = ['Baden-Württemberg', 'Bayern', 'Berlin', 'Brandenburg', 'Bremen', 'Hamburg', 'Hessen', 'Mecklenburg-Vorpommern', 'Niedersachsen', 'Nordrhein-Westfalen', 'Rheinland-Pfalz', 'Saarland', 'Sachsen', 'Sachsen-Anhalt', 'Schleswig-Holstein', 'Thüringen']
REGION_CODE = {key(s): s for s in STATES}
REGION_CODE.update({key(k): v for k, v in {'BW': 'Baden-Württemberg', 'BY': 'Bayern', 'BE': 'Berlin', 'BB': 'Brandenburg', 'HB': 'Bremen', 'HH': 'Hamburg', 'HE': 'Hessen', 'MV': 'Mecklenburg-Vorpommern', 'NI': 'Niedersachsen', 'NDS': 'Niedersachsen', 'NW': 'Nordrhein-Westfalen', 'NRW': 'Nordrhein-Westfalen', 'RP': 'Rheinland-Pfalz', 'SL': 'Saarland', 'SN': 'Sachsen', 'ST': 'Sachsen-Anhalt', 'SA': 'Sachsen-Anhalt', 'SH': 'Schleswig-Holstein', 'TH': 'Thüringen', 'Bavaria': 'Bayern', 'Hesse': 'Hessen', 'North Rhine-Westphalia': 'Nordrhein-Westfalen', 'Lower Saxony': 'Niedersachsen', 'Saxony': 'Sachsen', 'Saxony-Anhalt': 'Sachsen-Anhalt', 'Thuringia': 'Thüringen', 'Rhineland-Palatinate': 'Rheinland-Pfalz', 'Baden-Wurttemberg': 'Baden-Württemberg', 'Mecklenburg-Western Pomerania': 'Mecklenburg-Vorpommern', 'Nordrhein_Westfalen': 'Nordrhein-Westfalen', 'Baden_Wuerttemberg': 'Baden-Württemberg', 'Rheinland_Pfalz': 'Rheinland-Pfalz', 'Sachsen_Anhalt': 'Sachsen-Anhalt', 'Schleswig_Holstein': 'Schleswig-Holstein', 'Mecklenburg_Vorpommern': 'Mecklenburg-Vorpommern', 'Thueringen': 'Thüringen', 'Baden-Wuerttemberg': 'Baden-Württemberg'}.items()})
_GAZ = None


def fill_region(city, region='', country='DE'):
    """Fill a missing Bundesland: explicit region code first, then the learned gazetteer."""
    global _GAZ
    if country != 'DE': return region
    if region: return REGION_CODE.get(key(region), region)
    if _GAZ is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / 'data/geo_cities.json'
        _GAZ = json.loads(p.read_text()) if p.exists() else {}
    c = key(city)
    for cand in (c, re.split(r'[-(/,]| am | an der | im | ob der | bei ', c)[0].strip()):
        if cand in CITY: return CITY[cand][1]
        if cand in _GAZ: return _GAZ[cand]
    return ''


ALIAS = {'munich': 'München', 'vienna': 'Wien', 'zurich': 'Zürich', 'cologne': 'Köln', 'nuremberg': 'Nürnberg', 'hanover': 'Hannover', 'geneva': 'Genf', 'lucerne': 'Luzern', 'frankfurt': 'Frankfurt am Main'}


def locate(locations, country='', remote=False, personio=False, german_office=False):
    explicit = COUNTRY.get(key(country), '')
    fallback = None
    for location in locations:
        text = str(location or '')
        if FOREIGN.search(text) and not re.search(r'\b(?:Deutschland|Germany|Österreich|Austria|Schweiz|Switzerland)\b', text): continue
        city = re.sub(r'\s*\((?:Hybrid|Remote|On.?site)\)\s*', '', text, flags=re.I)
        city = re.sub(r'^Remote\s*[-–:]\s*', '', city, flags=re.I).strip()
        city = re.sub(r'\s*\(\s*\d{4,5}\s*\)|^\s*\d{4,5}\s+|^(?:DEU|AUT|CHE|DE|AT|CH)[_ -]', '', city).strip()
        pieces = re.split(r'[,;/|]|\s+[-–]\s+', city)
        found_country = next((COUNTRY[key(p)] for p in pieces if key(p) in COUNTRY), explicit)
        for piece in pieces:
            if key(piece) in CITY:
                code, region = CITY[key(piece)]
                return ALIAS.get(key(piece), piece.strip()), code, region
        if found_country and fallback is None:
            fallback = (pieces[0].strip() if key(pieces[0]) not in COUNTRY else '', found_country, {'AT': 'Österreich', 'CH': 'Schweiz'}.get(found_country, ''))
    if fallback: return fallback
    joined = ' '.join(str(x or '') for x in locations)
    # Wort-Scan für Freitext-Orte ("Munich Hybrid (NavVis GmbH)", "Berlin HQ", "Hinterm Hauptbahnhof 3-5, 76137 Karlsruhe")
    if not NON_DACH.search(joined):
        words = re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß.-]*", joined)
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                cand = key(' '.join(words[i:i + n]))
                if cand in CITY:
                    code, region = CITY[cand]
                    return ALIAS.get(cand, ' '.join(words[i:i + n])), code, region
        m = re.search(r'\b\d{5}\s+([A-ZÄÖÜ][\wäöüß.-]+(?:\s+(?:am|an der|im|bei)\s+[A-ZÄÖÜ][\wäöüß.-]+)?)', joined)
        if m:  # deutsches Adressformat "PLZ Ort"
            return m.group(1), 'DE', fill_region(m.group(1))
    if explicit:
        return joined, explicit, {'AT': 'Österreich', 'CH': 'Schweiz'}.get(explicit, '')
    if remote and re.search(r'\b(DE|AT|CH|DACH|Germany|Deutschland|Austria|Österreich|Switzerland|Schweiz)\b', joined, re.I):
        return '', 'DE', ''
    if personio and not country and german_office and not NON_DACH.search(joined):
        return joined, 'DE', ''
    return None


_PLZ = {}
for _r, _st in [('01-02,04-05,08-09', 'Sachsen'), ('03', 'Brandenburg'), ('06', 'Sachsen-Anhalt'), ('07', 'Thüringen'), ('10-13', 'Berlin'), ('14-16', 'Brandenburg'),
                ('17-19', 'Mecklenburg-Vorpommern'), ('20,22', 'Hamburg'), ('21,26-27,29-31,37-38,49', 'Niedersachsen'), ('23-25', 'Schleswig-Holstein'), ('28', 'Bremen'),
                ('32-33,40-48,50-53,57-59', 'Nordrhein-Westfalen'), ('34-36,60-61,63-65', 'Hessen'), ('39', 'Sachsen-Anhalt'), ('54-56,67', 'Rheinland-Pfalz'),
                ('66', 'Saarland'), ('68-79,88-89', 'Baden-Württemberg'), ('80-87,90-97', 'Bayern'), ('98-99', 'Thüringen')]:
    for _part in _r.split(','):
        _a, _b = (_part.split('-') + [_part])[:2]
        for _n in range(int(_a), int(_b) + 1): _PLZ[f'{_n:02d}'] = _st


def region_from_plz(plz):
    """Näherung: Bundesland aus den ersten zwei PLZ-Ziffern (Grenzgebiete können abweichen)."""
    plz = str(plz or '').strip()
    return _PLZ.get(plz[:2], '') if re.fullmatch(r'\d{5}', plz) else ''
