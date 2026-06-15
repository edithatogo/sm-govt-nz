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
