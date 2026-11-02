import React, {useEffect, useState} from 'react';
import {
  View, Text, ScrollView, TextInput, TouchableOpacity, ActivityIndicator,
  StyleSheet, Alert, Image, Linking, Share, Platform, StatusBar as RNStatusBar
} from 'react-native';
import {StatusBar} from 'expo-status-bar';
import * as ImagePicker from 'expo-image-picker';
import {verifyText,verifyLink,verifyImage,getHistory,getSources,getVerification,testBackend} from './src/api';
import {C} from './src/theme';
import type {HistoryItem, Source, Verification, SelectedImage, Verdict} from './src/types';

type Tab='analyser'|'historique'|'sources'|'reglages';
type Mode='texte'|'lien'|'capture';
const DEFAULT_API=process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.42:8000';
const STATUSES:Record<Verdict,{name:string;fg:string;bg:string}>={
  a_verifier:{name:'À VÉRIFIER',fg:C.amber,bg:C.lightAmber},
  corrobore:{name:'CORROBORÉ PAR FACT-CHECK',fg:C.green,bg:C.lightGreen},
  contredit:{name:'CONTESTÉ PAR FACT-CHECK',fg:C.red,bg:C.lightRed}
};
function Action({title,onPress,primary=false,disabled=false}: {
  title:string;onPress:()=>void;primary?:boolean;disabled?:boolean
}){
  return <TouchableOpacity disabled={disabled} onPress={onPress} style={[
    s.action,primary ? s.actionPrimary : s.actionSecondary,disabled && {opacity:.55}
  ]}><Text style={[s.actionText,primary ? {color:C.white}:{color:C.navy}]}>{title}</Text></TouchableOpacity>;
}
function Tag({value}:{value:Verdict}){
  const color=STATUSES[value]||STATUSES.a_verifier;
  return <View style={[s.tag,{backgroundColor:color.bg}]}><Text style={[s.tagText,{color:color.fg}]}>{color.name}</Text></View>;
}
function Panel({children}:{children:React.ReactNode}){
  return <View style={s.panel}>{children}</View>;
}
function Headline({title,subtitle}:{title:string;subtitle?:string}){
  return <View style={{marginBottom:16}}><Text style={s.heading}>{title}</Text>
      {!!subtitle && <Text style={s.description}>{subtitle}</Text>}</View>;
}
async function externalLink(url:string){
  try {await Linking.openURL(url);}catch{Alert.alert('Impossible d’ouvrir le lien',url);}
}
export default function App(){
  const [tab,setTab]=useState<Tab>('analyser');
  const [mode,setMode]=useState<Mode>('texte');
  const [apiUrl,setApiUrl]=useState(DEFAULT_API);
  const [body,setBody]=useState('');
  const [url,setUrl]=useState('');
  const [image,setImage]=useState<SelectedImage|null>(null);
  const [result,setResult]=useState<Verification|null>(null);
  const [busy,setBusy]=useState(false);
  const [connectBusy,setConnectBusy]=useState(false);
  const [connectMsg,setConnectMsg]=useState('');
  const [history,setHistory]=useState<HistoryItem[]>([]);
  const [sources,setSources]=useState<Source[]>([]);
  const [docCount,setDocCount]=useState(0);
  const [listBusy,setListBusy]=useState(false);
  const [listError,setListError]=useState('');

  const refresh=async (dest:Tab)=>{
    setListBusy(true);setListError('');
    try {
      if(dest==='historique')setHistory((await getHistory(apiUrl)).items);
      if(dest==='sources'){
        const response=await getSources(apiUrl);
        setSources(response.sources);setDocCount(response.documents_count);
      }
    }catch(e:any){setListError(e.message||String(e));}
    finally{setListBusy(false);}
  };
  useEffect(()=>{if(tab==='historique'||tab==='sources')void refresh(tab);},[tab]);
  const pickImage=async (camera:boolean)=>{
    if(camera){
      const permission=await ImagePicker.requestCameraPermissionsAsync();
      if(!permission.granted){Alert.alert('Autorisation nécessaire','Autorisez la caméra.');return;}
    }
    try{
      const res=camera
       ? await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:.85,allowsEditing:true})
       : await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:.85,allowsEditing:true});
      if(!res.canceled&&res.assets.length){
        const a=res.assets[0];setImage({uri:a.uri,fileName:a.fileName,mimeType:a.mimeType});setResult(null);
      }
    }catch(e:any){Alert.alert('Image',e.message||'Impossible de sélectionner cette image.');}
  };
  const submit=async()=>{
    setBusy(true);setResult(null);
    try{
      let data:Verification;
      if(mode==='texte'){
        if(body.trim().length<5)throw Error('Ajoutez au moins cinq caractères.');
        data=await verifyText(apiUrl,body.trim());
      } else if(mode==='lien'){
        if(!/^https?:\/\//i.test(url.trim()))throw Error('Collez un lien complet commençant par https://');
        data=await verifyLink(apiUrl,url.trim());
      } else {
        if(!image)throw Error('Sélectionnez une image ou photographiez un document.');
        data=await verifyImage(apiUrl,image);
      }
      setResult(data);
    }catch(e:any){Alert.alert('Analyse impossible',e.message||'Erreur inconnue');}
    finally{setBusy(false);}
  };
  const shareReport=async()=>{
    if(!result)return;
    const lines=[`HAMARINO — Vérification ${result.id}`,`Affirmation : ${result.claim}`,
      `Évaluation : ${STATUSES[result.verdict].name}`,result.summary,'',
      ...result.evidence.map((e,i)=>`Source ${i+1}: ${e.title} — ${e.url}\nExtrait : ${e.passage}`),
      ...result.factchecks.map((f,i)=>`Fact-check ${i+1}: ${f.publisher}, ${f.rating} — ${f.url}`),
      '',result.warning];
    await Share.share({message:lines.join('\n')});
  };
  const tabs:[Tab,string,string][]=[
    ['analyser','⌕','Analyser'],['historique','◷','Historique'],
    ['sources','▤','Sources'],['reglages','⚙','Réglages']
  ];
  return <View style={s.root}>
    <StatusBar style="light" />
    <View style={s.topSafe}/>
    <View style={s.banner}>
      <Text style={s.brandSmall}>IFM  /  HACKATHON FANILO</Text>
      <Text style={s.brand}>HAMARINO<Text style={{color:C.gold}}>•</Text></Text>
      <Text style={s.brandCaption}>Vérifier les faits. Remonter aux sources.</Text>
    </View>
    <ScrollView style={s.scroll} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      {tab==='analyser'&&<>
        <Headline title="Examiner une information" subtitle="Une analyse assistée par des sources, jamais un jugement automatique."/>
        <View style={s.modeRow}>
          {([['texte','✎ Texte'],['lien','↗ Lien'],['capture','▧ Capture']] as const).map(([key,label])=>
            <TouchableOpacity key={key} style={[s.mode,mode===key&&s.modeActive]}
             onPress={()=>{setMode(key);setResult(null);}}>
              <Text style={[s.modeText,mode===key&&{color:C.white}]}>{label}</Text>
            </TouchableOpacity>)}
        </View>
        <Panel>
          {mode==='texte'&&<>
            <Text style={s.fieldLabel}>Texte ou affirmation à vérifier</Text>
            <TextInput multiline value={body} onChangeText={setBody} maxLength={10000}
              textAlignVertical="top" style={[s.input,{minHeight:150}]}
              placeholder="Ex. Une publication affirme que…" placeholderTextColor="#8896A4"/>
            <Text style={s.hint}>Saisissez une affirmation précise, avec une date ou un lieu si possible.</Text>
          </>}
          {mode==='lien'&&<>
            <Text style={s.fieldLabel}>URL d’un article ou d’une page publique</Text>
            <TextInput value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false}
              keyboardType="url" style={s.input} placeholder="https://exemple.mg/article"
              placeholderTextColor="#8896A4"/>
            <Text style={s.hint}>Certaines plateformes sociales bloquent la lecture automatique des pages.</Text>
          </>}
          {mode==='capture'&&<>
            <Text style={s.fieldLabel}>Image d’une publication ou d’un document</Text>
            <View style={s.pickerRow}>
              <Action title="📷 Appareil photo" onPress={()=>void pickImage(true)}/>
              <Action title="▧ Galerie" onPress={()=>void pickImage(false)}/>
            </View>
            {!!image&&<Image source={{uri:image.uri}} resizeMode="contain" style={s.preview}/>}
            <Text style={s.hint}>L’OCR Tesseract s’exécute sur le backend. JPG/PNG/WEBP conseillés.</Text>
          </>}
          <View style={{height:18}}/>
          <Action title={busy?'Analyse en cours…':'Lancer la vérification'} onPress={()=>void submit()} primary disabled={busy}/>
          {busy&&<ActivityIndicator color={C.blue} style={{marginTop:14}}/>}
        </Panel>
        {!!result&&<>
          <View style={{height:18}}/>
          <ResultCard result={result} shareReport={()=>void shareReport()}/>
        </>}
        <Text style={s.bottomNote}>Le résultat « À vérifier » n’est pas une preuve de fausseté. Un recoupement humain reste nécessaire.</Text>
      </>}
      {tab==='historique'&&<>
        <Headline title="Historique des analyses" subtitle="Enregistré dans la base SQLite du serveur."/>
        <Action title="Actualiser" onPress={()=>void refresh('historique')}/>
        {listBusy&&<ActivityIndicator color={C.blue} style={{margin:20}}/>}
        {!!listError&&<Text style={s.error}>{listError}</Text>}
        {!listBusy&&history.length===0&&<Text style={s.empty}>Aucune analyse pour le moment.</Text>}
        {history.map(item=><TouchableOpacity key={item.id} style={s.historyCard}
          onPress={async()=>{
            try{const data=await getVerification(apiUrl,item.id);setResult(data);setTab('analyser');}
            catch(e:any){Alert.alert('Erreur',e.message);}
          }}>
          <Tag value={item.verdict}/>
          <Text style={s.historyText} numberOfLines={3}>{item.excerpt}</Text>
          <Text style={s.hint}>{item.created_at.replace('T',' ').slice(0,19)}  ·  Voir l’analyse ›</Text>
        </TouchableOpacity>)}
      </>}
      {tab==='sources'&&<>
        <Headline title="Sources et corpus RAG" subtitle="Catalogue éditorial : une source reconnue ne garantit pas chaque affirmation."/>
        <Action title="Actualiser la liste" onPress={()=>void refresh('sources')}/>
        <Panel>
          <Text style={s.metric}>{docCount}</Text>
          <Text style={s.description}>documents indexés pour la recherche de passages</Text>
          <Text style={s.hint}>Pour ajouter/actualiser les documents, voir les commandes admin du README.</Text>
        </Panel>
        {listBusy&&<ActivityIndicator color={C.blue} style={{margin:20}}/>}
        {!!listError&&<Text style={s.error}>{listError}</Text>}
        {sources.map(source=><TouchableOpacity key={source.id} style={s.historyCard}
           onPress={()=>void externalLink(source.website)}>
          <Text style={s.sourceTitle}>{source.name}  ↗</Text>
          <Text style={s.hint}>{source.category} · {source.rss_url?'Flux RSS configuré':'Import manuel de pages'}</Text>
          <Text style={s.link} numberOfLines={1}>{source.website}</Text>
        </TouchableOpacity>)}
      </>}
      {tab==='reglages'&&<>
        <Headline title="Connexion au backend" subtitle="Le téléphone et le PC doivent utiliser le même réseau local."/>
        <Panel>
          <Text style={s.fieldLabel}>URL du serveur FastAPI</Text>
          <TextInput value={apiUrl} onChangeText={setApiUrl} autoCapitalize="none"
            autoCorrect={false} style={s.input} keyboardType="url"/>
          <Text style={s.hint}>Exemple : http://192.168.1.42:8000 (pas localhost sur le téléphone)</Text>
          <View style={{height:14}}/>
          <Action title={connectBusy?'Vérification…':'Tester la connexion'} primary disabled={connectBusy}
           onPress={async()=>{
             setConnectBusy(true);setConnectMsg('');
             try{const x=await testBackend(apiUrl);setConnectMsg(`✓ Connecté à ${x.service}. ${x.ocr}`);}
             catch(e:any){setConnectMsg(`✕ ${e.message}`);}
             finally{setConnectBusy(false);}
           }}/>
          {!!connectMsg&&<Text style={[s.hint,{marginTop:14}]}>{connectMsg}</Text>}
        </Panel>
        <Panel>
          <Text style={s.fieldLabel}>À propos de HAMARINO</Text>
          <Text style={s.description}>Prototype FANILO / IFM — reconnaissance OCR, recherche augmentée par sources (RAG lexical) et contrôle humain.</Text>
          <Text style={s.hint}>Aucun secret API n’est stocké dans l’application mobile. Le réglage IP est temporaire : mettre à jour mobile/.env pour le conserver.</Text>
        </Panel>
      </>}
    </ScrollView>
    <View style={s.nav}>
      {tabs.map(([key,icon,label])=><TouchableOpacity key={key} onPress={()=>setTab(key)} style={s.navItem}>
        <Text style={[s.navIcon,tab===key&&{color:C.blue}]}>{icon}</Text>
        <Text style={[s.navLabel,tab===key&&{color:C.blue,fontWeight:'800'}]}>{label}</Text>
      </TouchableOpacity>)}
    </View>
  </View>;
}
function ResultCard({result,shareReport}:{result:Verification,shareReport:()=>void}){
  return <Panel>
    <View style={{flexDirection:'row',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
      <Text style={s.resultTitle}>Rapport d’analyse</Text><Tag value={result.verdict}/>
    </View>
    <Text style={s.fieldLabel}>Affirmation identifiée</Text>
    <Text selectable style={s.quote}>{result.claim}</Text>
    <Text style={s.description}>{result.summary}</Text>
    {!!result.extracted_text&&<View style={s.ocrBox}>
      <Text style={s.fieldLabel}>Texte extrait par OCR</Text>
      <Text selectable style={s.ocrText}>{result.extracted_text}</Text>
    </View>}
    <Text style={s.sectionTitle}>Sources proches ({result.evidence.length})</Text>
    {result.evidence.length===0&&<Text style={s.description}>Aucun passage trouvé. Actualisez le corpus ou renseignez d’autres sources.</Text>}
    {result.evidence.map((item,i)=><View key={item.document_id} style={s.evidence}>
      <Text style={s.sourceTitle}>{i+1}. {item.title}</Text>
      <Text style={s.hint}>{item.source_name}  ·  pertinence {Math.round(item.relevance*100)} %</Text>
      <Text style={s.passage} selectable>« {item.passage} »</Text>
      <TouchableOpacity onPress={()=>void externalLink(item.url)}><Text style={s.link}>Consulter l’original ↗</Text></TouchableOpacity>
    </View>)}
    <Text style={s.sectionTitle}>Fact-checks publiés ({result.factchecks.length})</Text>
    {result.factchecks.length===0&&<Text style={s.description}>Aucun avis externe lié ou API non configurée.</Text>}
    {result.factchecks.map((x,i)=><View key={`${x.url}-${i}`} style={s.evidence}>
      <Text style={s.sourceTitle}>{x.publisher||'Organisme de fact-checking'}</Text>
      <Text style={s.description}>Évaluation publiée : {x.rating}</Text>
      <TouchableOpacity onPress={()=>void externalLink(x.url)}><Text style={s.link}>Lire la vérification ↗</Text></TouchableOpacity>
    </View>)}
    <View style={s.warning}><Text style={s.warningText}>{result.warning}</Text></View>
    <Action title="Partager le rapport" onPress={shareReport}/>
  </Panel>;
}
const s=StyleSheet.create({
  root:{flex:1,backgroundColor:C.cream},
  topSafe:{height:Platform.OS==='android' ? (RNStatusBar.currentHeight||24) : 50,backgroundColor:C.navy},
  banner:{backgroundColor:C.navy,paddingHorizontal:24,paddingTop:12,paddingBottom:22},
  brandSmall:{fontSize:10,color:'#A5C5DD',letterSpacing:2,fontWeight:'700'},
  brand:{fontSize:30,color:C.white,fontWeight:'900',letterSpacing:1.2,marginTop:5},
  brandCaption:{fontSize:12,color:'#BDCEDB',marginTop:2},
  scroll:{flex:1},content:{padding:18,paddingBottom:36},
  heading:{fontSize:22,color:C.navy,fontWeight:'800'},
  description:{color:C.muted,fontSize:13,lineHeight:20,marginTop:5},
  modeRow:{flexDirection:'row',gap:8,marginBottom:14},
  mode:{flex:1,backgroundColor:'#E6EBF1',borderRadius:12,alignItems:'center',paddingVertical:12},
  modeActive:{backgroundColor:C.blue},modeText:{fontSize:13,color:C.blue,fontWeight:'800'},
  panel:{backgroundColor:C.white,borderRadius:18,padding:18,marginBottom:14,borderWidth:1,borderColor:C.border},
  fieldLabel:{color:C.navy,fontWeight:'800',fontSize:13,marginBottom:8},
  input:{color:C.text,backgroundColor:'#FBFCFD',borderWidth:1,borderColor:C.border,borderRadius:11,padding:13,fontSize:14},
  hint:{fontSize:11,lineHeight:17,color:C.muted,marginTop:8},
  pickerRow:{flexDirection:'row',gap:8,flexWrap:'wrap'},
  action:{paddingVertical:13,paddingHorizontal:15,borderRadius:12,alignItems:'center',justifyContent:'center'},
  actionPrimary:{backgroundColor:C.blue},actionSecondary:{backgroundColor:'#E8EFF5'},
  actionText:{fontWeight:'800',fontSize:13},
  preview:{height:190,width:'100%',borderRadius:10,marginTop:14,backgroundColor:'#E7E9EC'},
  bottomNote:{fontSize:11,lineHeight:18,color:C.muted,marginTop:8,marginHorizontal:6},
  tag:{borderRadius:8,paddingHorizontal:8,paddingVertical:6,alignSelf:'flex-start'},
  tagText:{fontSize:9,fontWeight:'900',letterSpacing:.2},
  resultTitle:{fontSize:16,color:C.navy,fontWeight:'900',flexShrink:1},
  quote:{fontSize:15,fontWeight:'700',color:C.navy,backgroundColor:'#F3F7FA',borderLeftWidth:3,borderColor:C.gold,
    padding:13,marginBottom:12,lineHeight:22},
  sectionTitle:{fontSize:16,fontWeight:'900',color:C.navy,marginTop:18,marginBottom:8},
  evidence:{paddingVertical:12,borderBottomColor:C.border,borderBottomWidth:1},
  sourceTitle:{fontWeight:'800',fontSize:13,color:C.text},
  passage:{color:C.text,lineHeight:19,fontSize:12,marginVertical:9},
  link:{color:'#2066A7',fontSize:12,fontWeight:'800',marginTop:7},
  ocrBox:{padding:12,marginTop:14,backgroundColor:'#F3F7FA',borderRadius:10},
  ocrText:{fontSize:12,color:C.text,lineHeight:19,maxHeight:150},
  warning:{backgroundColor:C.lightAmber,padding:13,borderRadius:10,marginVertical:16},
  warningText:{color:C.amber,fontSize:11,lineHeight:18},
  metric:{fontSize:36,color:C.navy,fontWeight:'900'},
  nav:{flexDirection:'row',backgroundColor:C.white,borderTopWidth:1,borderTopColor:C.border,paddingBottom:Platform.OS==='ios'?19:8,paddingTop:8},
  navItem:{flex:1,alignItems:'center',paddingVertical:4},
  navIcon:{fontSize:21,color:'#8A9BAD',marginBottom:2},
  navLabel:{fontSize:10,color:C.muted},
  historyCard:{backgroundColor:C.white,borderColor:C.border,borderWidth:1,padding:16,borderRadius:13,marginTop:10},
  historyText:{fontSize:13,color:C.text,lineHeight:19,marginTop:10},
  error:{color:C.red,fontSize:13,marginVertical:15},
  empty:{color:C.muted,marginVertical:20,textAlign:'center'}
});
