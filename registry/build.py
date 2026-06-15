import json

def make(pid,name,hon,party,el,mt,gen,lr=None,soc=None):
    p = {"person_id":pid,"full_name":name,"honorific":hon,"party_id":party,"electorate":el,"member_type":mt,"gender":gen,"image_url":f"https://www.parliament.nz/media/{pid}-portrait.jpg","biography_url":f"https://www.parliament.nz/en/mps-and-electorates/members-of-parliament/{pid}/","social_profiles":soc or {}}
    if lr is not None:
        p["list_rank"] = lr
    return p

def rl(rid,title,org,orgn,cat,port=None,sd="2023-11-27",ed=None,ic=True):
    r = {"role_id":rid,"title":title,"organization":org,"organization_name":orgn,"category":cat,"start_date":sd,"end_date":ed,"is_current":ic}
    if port:
        r["portfolio"] = port
    return r

persons = []
print("Script loaded")
# === NATIONAL PARTY ===
p1 = [
("christopher-luxon","Christopher Mark Luxon","Rt Hon","Botany",True,"male"),
("nicola-willis","Nicola Valentine Willis","Hon","List",False,"female"),
("chris-bishop","Christopher Bishop","Hon","Hutt South",True,"male"),
("simeon-brown","Simeon Brown","Hon","Pakuranga",True,"male"),
("erica-stanford","Erica Stanford","Hon","East Coast Bays",True,"female"),
("paul-goldsmith","Paul Goldsmith","Hon","List",False,"male"),
("louise-upston","Louise Upston","Hon","Taupō",True,"female"),
("judith-collins","Judith Collins","Rt Hon","Papakura",True,"female"),
("shane-reti","Shane Reti","Hon","Whangārei",True,"male"),
("mark-mitchell","Mark Mitchell","Hon","Whangaparāoa",True,"male"),
("todd-mcclay","Todd McClay","Hon","Rotorua",True,"male"),
("tama-potaka","Tama Potaka","Hon","Hamilton West",True,"male"),
("matt-doocey","Matt Doocey","Hon","Waimakariri",True,"male"),
("simon-watts","Simon Watts","Hon","North Shore",True,"male"),
("chris-penk","Chris Penk","Hon","Kaipara ki Mahurangi",True,"male"),
("penny-simmonds","Penny Simmonds","Hon","Invercargill",True,"female"),
("nicola-grigg","Nicola Grigg","Hon","Selwyn",True,"female"),
("james-meager","James Meager","Hon","Rangitata",True,"male"),
("scott-simpson","Scott Simpson","Hon","Coromandel",True,"male"),
("gerry-brownlee","Gerry Brownlee","Rt Hon","List",False,"male"),
("barbara-kuriger","Barbara Kuriger","Hon","Taranaki-King Country",True,"female"),
("maureen-pugh","Maureen Pugh","Hon","West Coast-Tasman",True,"female"),
]
for pid,name,hon,el,iselect,gen in p1:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"national",el,mt,gen))
print(f"Added {len(p1)} National Party MPs")
# More National MPs (backbenchers)
p2 = [
("stuart-smith","Stuart Smith","Kaikōura",True,"male"),
("suzanne-redmayne","Suze Redmayne","Rangitīkei",True,"female"),
("melissa-lee","Melissa Lee","List",False,"female"),
("andrew-bayly","Andrew Bayly","Port Waikato",True,"male"),
("nancy-lu","Nancy Lu","List",False,"female"),
("katie-nimon","Katie Nimon","Napier",True,"female"),
("catherine-wedd","Catherine Wedd","Tukituki",True,"female"),
("paulo-garcia","Paulo Garcia","New Lynn",True,"male"),
("vanessa-weenink","Vanessa Weenink","Banks Peninsula",True,"female"),
("rima-nakhle","Rima Nakhle","Takanini",True,"female"),
("dana-kirkpatrick","Dana Kirkpatrick","East Coast",True,"female"),
("carl-bates","Carl Bates","Whanganui",True,"male"),
("carlos-cheung","Carlos Cheung","Mount Roskill",True,"male"),
("joseph-mooney","Joseph Mooney","Southland",True,"male"),
("sam-uffindell","Sam Uffindell","Tauranga",True,"male"),
("tim-van-de-molen","Tim van de Molen","Waikato",True,"male"),
("miles-anderson","Miles Anderson","Waitaki",True,"male"),
("dan-bidois","Dan Bidois","Northcote",True,"male"),
("mike-butterick","Mike Butterick","Wairarapa",True,"male"),
("cameron-brewer","Cameron Brewer","Upper Harbour",True,"male"),
("hamish-campbell","Hamish Campbell","Ilam",True,"male"),
("tim-costley","Tim Costley","Ōtaki",True,"male"),
("greg-fleming","Greg Fleming","Maungakiekie",True,"male"),
("ryan-hamilton","Ryan Hamilton","Hamilton East",True,"male"),
("david-macleod","David MacLeod","New Plymouth",True,"male"),
("grant-mccallum","Grant McCallum","Northland",True,"male"),
("tom-rutherford","Tom Rutherford","Bay of Plenty",True,"male"),
]
for pid,name,el,iselect,gen in p2:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,"","national",el,mt,gen))
print(f"Added {len(p2)} more National MPs")
print(f"Total: {len(persons)}")
# === LABOUR PARTY (34 MPs) ===
pl = [
("chris-hipkins","Chris Hipkins","Rt Hon","Remutaka",True,"male"),
("carmel-sepuloni","Carmel Sepuloni","Hon","Kelston",True,"female"),
("barbara-edmonds","Barbara Edmonds","Hon","Mana",True,"female"),
("megan-woods","Megan Woods","Hon","Wigram",True,"female"),
("willie-jackson","Willie Jackson","Hon","List",False,"male"),
("ayesha-verrall","Ayesha Verrall","Hon","List",False,"female"),
("kieran-mcanulty","Kieran McAnulty","Hon","List",False,"male"),
("willow-jean-prime","Willow-Jean Prime","Hon","List",False,"female"),
("ginny-andersen","Ginny Andersen","Hon","List",False,"female"),
("jan-tinetti","Jan Tinetti","Hon","List",False,"female"),
("peeni-henare","Peeni Henare","Hon","List",False,"male"),
("tangi-utikere","Tangi Utikere","Hon","Palmerston North",True,"male"),
("priyanca-radhakrishnan","Priyanca Radhakrishnan","Hon","List",False,"female"),
("jo-luxton","Jo Luxton","Hon","List",False,"female"),
("duncan-webb","Duncan Webb","Hon","Christchurch Central",True,"male"),
("deborah-russell","Deborah Russell","Hon","List",False,"female"),
("rachel-brooking","Rachel Brooking","Hon","Dunedin",True,"female"),
("damien-oconnor","Damien O'Connor","Hon","List",False,"male"),
("camilla-belich","Camilla Belich","Hon","List",False,"female"),
("arena-williams","Arena Williams","Hon","Manurewa",True,"female"),
("phil-twyford","Phil Twyford","Hon","Te Atatū",True,"male"),
("greg-oconnor","Greg O'Connor","Hon","Ōhāriu",True,"male"),
("jenny-salesa","Jenny Salesa","Hon","Panmure-Ōtāhuhu",True,"female"),
("rachel-boyack","Rachel Boyack","","Nelson",True,"female"),
("adrian-rurawhe","Adrian Rurawhe","Hon","List",False,"male"),
("helen-white","Helen White","","Mount Albert",True,"female"),
("ingrid-leary","Ingrid Leary","","Taieri",True,"female"),
("lemauga-lydia-sosene","Lemauga Lydia Sosene","","Māngere",True,"female"),
("reuben-davidson","Reuben Davidson","","Christchurch East",True,"male"),
("cushla-tangaere-manuel","Cushla Tangaere-Manuel","","Ikaroa-Rawhiti",True,"female"),
("tracey-mclellan","Tracey McLellan","","List",False,"female"),
("shanan-halbert","Shanan Halbert","","List",False,"male"),
("glen-bennett","Glen Bennett","","List",False,"male"),
("vanushi-walters","Vanushi Walters","","List",False,"female"),
]
for pid,name,hon,el,iselect,gen in pl:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"labour",el,mt,gen))
print(f"Added {len(pl)} Labour MPs")
print(f"Total: {len(persons)}")
# === GREEN PARTY (15 MPs) ===
pg = [
("marama-davidson","Marama Davidson","Hon","List",False,"female"),
("chlöe-swarbrick","Chlöe Swarbrick","","Auckland Central",True,"female"),
("julie-anne-genter","Julie Anne Genter","Hon","Rongotai",True,"female"),
("teanau-tuiono","Teanau Tuiono","","List",False,"male"),
("lan-pham","Lan Pham","","List",False,"female"),
("ricardo-menendez-march","Ricardo Menéndez March","","List",False,"male"),
("steve-abel","Steve Abel","","List",False,"male"),
("hūhana-lyndon","Hūhana Lyndon","","List",False,"female"),
("scott-willis","Scott Willis","","List",False,"male"),
("kahurangi-carter","Kahurangi Carter","","List",False,"female"),
("celia-wade-brown","Celia Wade-Brown","","List",False,"female"),
("lawrence-xu-nan","Lawrence Xu-Nan","","List",False,"male"),
("francisco-hernandez","Francisco Hernandez","","List",False,"male"),
("mike-davidson","Mike Davidson","","List",False,"male"),
("tamatha-paul","Tamatha Paul","","Wellington Central",True,"female"),
]
for pid,name,hon,el,iselect,gen in pg:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"green",el,mt,gen))
print(f"Added {len(pg)} Green MPs")
print(f"Total: {len(persons)}")
# === ACT PARTY (11 MPs) ===
pa = [
("david-seymour","David Seymour","Hon","Epsom",True,"male"),
("brooke-van-velden","Brooke van Velden","Hon","Tāmaki",True,"female"),
("nicole-mckee","Nicole McKee","Hon","List",False,"female"),
("andrew-hoggard","Andrew Hoggard","Hon","List",False,"male"),
("karen-chhour","Karen Chhour","Hon","List",False,"female"),
("simon-court","Simon Court","","List",False,"male"),
("todd-stephenson","Todd Stephenson","","List",False,"male"),
("mark-cameron","Mark Cameron","","List",False,"male"),
("parmjeet-parmar","Parmjeet Parmar","","List",False,"female"),
("laura-mcclure","Laura McClure","","List",False,"female"),
("cameron-luxton","Cameron Luxton","","List",False,"male"),
]
for pid,name,hon,el,iselect,gen in pa:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"act",el,mt,gen))
print(f"Added {len(pa)} ACT MPs")
print(f"Total: {len(persons)}")
# === NZ FIRST PARTY (8 MPs) ===
pn = [
("winston-peters","Winston Peters","Rt Hon","List",False,"male"),
("shane-jones","Shane Jones","Hon","List",False,"male"),
("casey-costello","Casey Costello","Hon","List",False,"female"),
("mark-patterson","Mark Patterson","Hon","List",False,"male"),
("jenny-marcroft","Jenny Marcroft","","List",False,"female"),
("jamie-arbuckle","Jamie Arbuckle","","List",False,"male"),
("andy-foster","Andy Foster","","List",False,"male"),
("david-wilson","David Wilson","","List",False,"male"),
]
for pid,name,hon,el,iselect,gen in pn:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"nz-first",el,mt,gen))
print(f"Added {len(pn)} NZ First MPs")
print(f"Total: {len(persons)}")
# === TE PATI MAORI (6 MPs) ===
pt = [
("rawiri-waititi","Rawiri Waititi","","Waiariki",True,"male"),
("debbie-ngarewa-packer","Debbie Ngarewa-Packer","Hon","Te Tai Hauāuru",True,"female"),
("hana-rawhiti-maipi-clarke","Hana-Rawhiti Maipi-Clarke","","Hauraki-Waikato",True,"female"),
("orini-kaipara","Oriini Kaipara","","Tāmaki Makaurau",True,"female"),
("tākuta-ferris","Tākuta Ferris","","Te Tai Tonga",True,"male"),
("mariameno-kapa-kingi","Mariameno Kapa-Kingi","","Te Tai Tokerau",True,"female"),
]
for pid,name,hon,el,iselect,gen in pt:
    mt = "electorate" if iselect else "list"
    persons.append(make(pid,name,hon,"te-pati-maori",el,mt,gen))
print(f"Added {len(pt)} Te Pāti Māori MPs")
print(f"Total: {len(persons)}")
# === SAVE TO PERSONS.JSON ===
# Add basic MP role for each person
for p in persons:
    if not p["roles"]:
        if p["member_type"] == "electorate":
            p["roles"].append(rl(f"mp-for-{p['person_id']}", f"Member of Parliament for {p['electorate']}", "nz-parliament", "New Zealand Parliament", "mp", sd="2023-10-14"))
        else:
            p["roles"].append(rl(f"mp-list-{p['party_id']}", f"Member of Parliament ({p['party_id'].upper()} Party List)", "nz-parliament", "New Zealand Parliament", "mp", sd="2023-10-14"))

with open("registry/persons.json", "w", encoding="utf-8") as f:
    json.dump(persons, f, indent=2, ensure_ascii=False)

print(f"Total MPs saved: {len(persons)}")

# Verify by party
from collections import Counter
party_count = Counter(p["party_id"] for p in persons)
for party, count in sorted(party_count.items()):
    print(f"  {party}: {count}")
