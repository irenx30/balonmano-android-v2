
package com.balonmano.app;

import android.app.*;
import android.os.Bundle;
import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
import android.graphics.Typeface;
import android.text.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

public class MainActivity extends Activity {
    DB db;
    LinearLayout root, content;
    TextView title, score;
    int currentMatch = -1;
    Integer selectedPlayer = null;
    String pendingAction = null;
    String pendingZone = null;
    int matchMinute = 1;

    // Listas EXACTAMENTE iguales a las de la app de Python (app_pyhton.py)
    static final String[] ZONAS = {
        "Extremo izquierdo", "6 metros", "Lateral izquierdo", "Central",
        "Lateral derecho", "Extremo derecho", "7 metros"
    };
    static final String[] TIPOS = {"Apoyo", "Salto", "Vaselina", "Rosca", "1x1"};
    static final String[] DIRECCIONES = {"Arriba", "Centro", "Abajo", "Izquierda", "Derecha"};

    int pad=18;
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        db=new DB(this);
        home();
    }

    TextView tv(String s,int size){
        TextView t=new TextView(this); t.setText(s); t.setTextSize(size); t.setTextColor(0xff17202a);
        t.setPadding(pad,pad,pad,pad); return t;
    }
    Button btn(String s){
        Button b=new Button(this); b.setText(s); b.setTextSize(17); b.setAllCaps(false);
        b.setMinHeight(58); b.setPadding(10,6,10,6); return b;
    }
    void base(String name){
        root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(0xfff7f7f7);
        title=tv(name,24); title.setTypeface(Typeface.DEFAULT,Typeface.BOLD); title.setTextColor(ColorPrimary());
        root.addView(title,new LinearLayout.LayoutParams(-1,-2));
        ScrollView sv=new ScrollView(this); content=new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL); content.setPadding(10,5,10,20);
        sv.addView(content); root.addView(sv,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout nav=new LinearLayout(this); nav.setOrientation(LinearLayout.HORIZONTAL);
        String[] ns={"🏠","▶️","👥","📊","📋"};
        for(String n:ns){Button b=btn(n); nav.addView(b,new LinearLayout.LayoutParams(0,62,1));
            if(n.equals("🏠"))b.setOnClickListener(v->home());
            if(n.equals("▶️"))b.setOnClickListener(v->ongoingSelect());
            if(n.equals("👥"))b.setOnClickListener(v->players());
            if(n.equals("📊"))b.setOnClickListener(v->stats());
            if(n.equals("📋"))b.setOnClickListener(v->matches());
        }
        root.addView(nav); setContentView(root);
    }
    int ColorPrimary(){return 0xff123b5d;}
    void add(View v){content.addView(v,new LinearLayout.LayoutParams(-1,-2));}
    void gap(){Space s=new Space(this); content.addView(s,new LinearLayout.LayoutParams(1,10));}

    // ============================================================
    // TABLAS DE ESTADÍSTICAS (formato tipo tabla, con scroll horizontal)
    // ============================================================
    TextView tableCell(String s, boolean header){
        TextView t=new TextView(this); t.setText(s==null?"":s);
        t.setPadding(20,16,20,16); t.setTextSize(13); t.setMinWidth(96);
        if(header){ t.setTypeface(Typeface.DEFAULT,Typeface.BOLD); t.setTextColor(0xffffffff); }
        else { t.setTextColor(0xff17202a); }
        return t;
    }
    TableLayout buildTable(String[] headers, List<String[]> rows){
        TableLayout t=new TableLayout(this);
        TableRow hr=new TableRow(this); hr.setBackgroundColor(ColorPrimary());
        for(String h:headers) hr.addView(tableCell(h,true));
        t.addView(hr);
        int i=0;
        for(String[] row:rows){
            TableRow r=new TableRow(this); r.setBackgroundColor(i%2==0?0xffffffff:0xffe9edf2);
            for(String v:row) r.addView(tableCell(v,false));
            t.addView(r); i++;
        }
        return t;
    }
    void addTable(String[] headers, List<String[]> rows){
        HorizontalScrollView sv=new HorizontalScrollView(this);
        sv.addView(buildTable(headers,rows));
        add(sv);
    }
    String pct(int part,int total){
        double p = total>0 ? (100.0*part/total) : 0;
        return String.format(Locale.getDefault(),"%.1f%%",p);
    }

    void home(){
        base("🤾 Balonmano");
        add(tv("Control de partidos y estadísticas",18));
        gap();
        Button p=btn("▶️  Partido en curso"); p.setOnClickListener(v->ongoingSelect()); add(p);
        Button pl=btn("👥  Jugadoras / plantilla"); pl.setOnClickListener(v->players()); add(pl);
        Button st=btn("📊  Estadísticas"); st.setOnClickListener(v->stats()); add(st);
        Button ma=btn("📋  Partidos"); ma.setOnClickListener(v->matches()); add(ma);
    }

    void matches(){
        base("📋 Partidos");
        Button n=btn("➕ Nuevo partido"); n.setOnClickListener(v->newMatch()); add(n); gap();
        Cursor c=db.q("SELECT id,equipo,rival,fecha,competicion,goles_favor,goles_contra FROM partidos ORDER BY fecha DESC,id DESC");
        while(c.moveToNext()){
            int id=c.getInt(0); String text=c.getString(1)+"  "+c.getInt(5)+" - "+c.getInt(6)+"  "+c.getString(2)+"\n"+c.getString(3)+" · "+(c.getString(4)==null?"":c.getString(4));
            LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.VERTICAL);
            TextView t=tv(text,17); t.setTypeface(Typeface.DEFAULT,Typeface.BOLD); row.addView(t);
            LinearLayout actions=new LinearLayout(this);
            Button open=btn("▶️ Abrir"); open.setOnClickListener(v->{currentMatch=id; matchMinute=1; ongoing();});
            Button del=btn("🗑️ Borrar"); del.setOnClickListener(v->confirmDeleteMatch(id));
            actions.addView(open,new LinearLayout.LayoutParams(0,58,1)); actions.addView(del,new LinearLayout.LayoutParams(0,58,1));
            row.addView(actions); content.addView(row);
        }
        c.close();
    }
    void confirmDeleteMatch(int id){
        new AlertDialog.Builder(this).setTitle("Borrar partido")
            .setMessage("Se borrarán también sus acciones, lanzamientos y estadísticas asociadas. ¿Continuar?")
            .setNegativeButton("Cancelar",null).setPositiveButton("Borrar",(d,w)->{db.deleteMatch(id); if(currentMatch==id)currentMatch=-1; matches();}).show();
    }
    void newMatch(){
        base("➕ Nuevo partido");
        EditText team=new EditText(this); team.setHint("Mi equipo"); add(team);
        EditText rival=new EditText(this); rival.setHint("Rival"); add(rival);
        EditText comp=new EditText(this); comp.setHint("Competición"); add(comp);
        EditText date=new EditText(this); date.setText(new SimpleDateFormat("yyyy-MM-dd",Locale.getDefault()).format(new Date())); add(date);
        Button save=btn("💾 Crear partido"); save.setOnClickListener(v->{
            if(team.getText().toString().trim().isEmpty()||rival.getText().toString().trim().isEmpty()){toast("Introduce equipo y rival");return;}
            currentMatch=db.insertMatch(team.getText().toString().trim(),rival.getText().toString().trim(),date.getText().toString(),comp.getText().toString());
            matchMinute=1;
            ongoing();
        }); add(save);
    }

    void ongoingSelect(){
        base("▶️ Partido en curso");
        Cursor c=db.q("SELECT id,equipo,rival,fecha,goles_favor,goles_contra FROM partidos ORDER BY fecha DESC,id DESC");
        add(tv("Selecciona el partido",18));
        while(c.moveToNext()){
            int id=c.getInt(0); Button b=btn(c.getString(1)+"  "+c.getInt(4)+" - "+c.getInt(5)+"  "+c.getString(2));
            b.setOnClickListener(v->{currentMatch=id; matchMinute=1; ongoing();}); add(b);
        }
        c.close();
        Button newb=btn("➕ Crear partido"); newb.setOnClickListener(v->newMatch()); add(newb);
    }

    void ongoing(){
        if(currentMatch<0){ongoingSelect();return;}
        base("▶️ Partido en curso");
        Cursor m=db.q("SELECT equipo,rival,goles_favor,goles_contra FROM partidos WHERE id="+currentMatch);
        if(m.moveToFirst()){
            score=tv(m.getString(0)+"   "+m.getInt(2)+" - "+m.getInt(3)+"   "+m.getString(1),25); score.setTypeface(Typeface.DEFAULT,Typeface.BOLD); score.setGravity(Gravity.CENTER); content.addView(score);
        } m.close();

        LinearLayout minRow=new LinearLayout(this); minRow.setOrientation(LinearLayout.HORIZONTAL); minRow.setGravity(Gravity.CENTER);
        minRow.addView(tv("⏱ Minuto: "+matchMinute,16));
        Button chMin=btn("✏️ Cambiar"); chMin.setOnClickListener(v->editMinute()); minRow.addView(chMin,new LinearLayout.LayoutParams(-2,58));
        content.addView(minRow);

        if(selectedPlayer==null) playerStep(); else actionStep();
        gap(); add(tv("Últimas acciones",19));
        Cursor a=db.q("SELECT a.id,a.minuto,a.accion,a.zona,a.resultado,j.nombre,j.dorsal FROM acciones a LEFT JOIN jugadores j ON j.id=a.jugador_id WHERE a.partido_id="+currentMatch+" ORDER BY a.id DESC LIMIT 12");
        while(a.moveToNext()){
            int id=a.getInt(0); String s=a.getInt(1)+"'  #"+a.getInt(6)+" "+a.getString(5)+"  "+a.getString(2);
            if(a.getString(3)!=null&&!a.getString(3).isEmpty())s+=" · "+a.getString(3); if(a.getString(4)!=null)s+=" · "+a.getString(4);
            LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); TextView t=tv(s,15); row.addView(t,new LinearLayout.LayoutParams(0,-2,1));
            Button d=btn("🗑️"); d.setOnClickListener(v->{db.deleteAction(id); db.recalc(currentMatch); ongoing();}); row.addView(d,new LinearLayout.LayoutParams(70,58)); content.addView(row);
        } a.close();
        Cursor lp=db.q("SELECT lp.id,lp.minuto,lp.resultado,j.nombre,j.dorsal FROM lanzamientos_porteria lp LEFT JOIN porteros p ON p.id=lp.portero_id LEFT JOIN jugadores j ON lower(j.nombre)=lower(p.nombre) AND j.dorsal=p.dorsal WHERE lp.partido_id="+currentMatch+" ORDER BY lp.id DESC LIMIT 8");
        while(lp.moveToNext()){
            int id=lp.getInt(0); String s="🧤 "+lp.getInt(1)+"'  #"+lp.getInt(4)+" "+(lp.getString(3)==null?"":lp.getString(3))+" · "+lp.getString(2);
            LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.addView(tv(s,15),new LinearLayout.LayoutParams(0,-2,1));
            Button d=btn("🗑️"); d.setOnClickListener(v->{db.deleteShot(id); db.recalc(currentMatch); ongoing();}); row.addView(d,new LinearLayout.LayoutParams(70,58)); content.addView(row);
        } lp.close();
    }

    void editMinute(){
        EditText e=new EditText(this); e.setInputType(InputType.TYPE_CLASS_NUMBER); e.setText(""+matchMinute);
        new AlertDialog.Builder(this).setTitle("Minuto").setView(e)
            .setNegativeButton("Cancelar",null)
            .setPositiveButton("Aceptar",(d,w)->{
                try{ matchMinute=Integer.parseInt(e.getText().toString().trim()); }catch(Exception ex){}
                ongoing();
            }).show();
    }
    int currentMinute(){ return matchMinute; }

    void playerStep(){
        add(tv("¿Quién?",20));
        Cursor c=db.q("SELECT id,nombre,dorsal,posicion FROM jugadores WHERE activo=1 ORDER BY dorsal,nombre");
        int count=0; LinearLayout grid=new LinearLayout(this); grid.setOrientation(LinearLayout.VERTICAL); LinearLayout line=null;
        while(c.moveToNext()){
            if(count%2==0){line=new LinearLayout(this); grid.addView(line);}
            int id=c.getInt(0); String s="#"+c.getInt(2)+"  "+c.getString(1);
            Button b=btn(s); b.setOnClickListener(v->{selectedPlayer=id; ongoing();}); line.addView(b,new LinearLayout.LayoutParams(0,62,1)); count++;
        } c.close(); add(grid);
        Button g=btn("🥅  Portería"); g.setOnClickListener(v->goalkeeperStep()); add(g);
    }
    void actionStep(){
        Cursor p=db.q("SELECT nombre,dorsal,posicion FROM jugadores WHERE id="+selectedPlayer); String name=""; int dorsal=0; String pos="";
        if(p.moveToFirst()){name=p.getString(0);dorsal=p.getInt(1);pos=p.getString(2);}p.close();
        add(tv("Jugadora: #"+dorsal+" "+name,19));
        Button back=btn("↩️ Cambiar jugadora"); back.setOnClickListener(v->{selectedPlayer=null;ongoing();}); add(back);
        add(tv("¿Qué ha hecho?",20));
        // Mismas 10 acciones que en la app de Python (ACCIONES_JUGADORAS + Exclusión)
        String[] acts={"⚽ Gol","🎯 Lanzamiento","🤝 Asistencia","❌ Pérdida","🔄 Recuperación","⚔️ 1x1 ganado","🛡️ 1x1 perdido","7️⃣ 7 metros","🟥 Exclusión","🏃 Contraataque"};
        for(String x:acts){Button b=btn(x); b.setOnClickListener(v->chooseAction(x)); add(b);}
    }
    void chooseAction(String x){
        String clean=x.replaceAll("^[^A-Za-zÁÉÍÓÚÜÑ0-9]+","").trim();
        if(clean.equals("Lanzamiento")){ chooseZone(); return; }
        if(clean.equals("7 metros")){ choose7mResult(); return; }
        if(clean.equals("Contraataque")){ chooseContraResult(); return; }
        // Acciones directas: Gol, Asistencia, Pérdida, Recuperación, 1x1 ganado, 1x1 perdido, Exclusión
        recordAction(clean,"","Éxito");
    }
    void chooseZone(){
        add(tv("¿Desde dónde ha lanzado?",20));
        for(String z:ZONAS){Button b=btn("📍 "+z); b.setOnClickListener(v->{pendingZone=z; chooseLanzamientoResultado();}); add(b);}
        Button back=btn("↩️ Volver a acciones"); back.setOnClickListener(v->{pendingZone=null; ongoing();}); add(back);
    }
    void chooseLanzamientoResultado(){
        add(tv("¿Cómo ha terminado el lanzamiento?",20));
        String[] rs={"⚽ Gol","🧤 Parada","❌ Fallo"};
        for(String x:rs){
            Button b=btn(x);
            String r=x.contains("Gol")?"Gol":(x.contains("Parada")?"Parada":"Fallo");
            b.setOnClickListener(v->recordAction("Lanzamiento",pendingZone,r));
            add(b);
        }
    }
    void choose7mResult(){
        add(tv("7 metros: ¿qué ha ocurrido?",20));
        String[] rs={"⚽ Gol","🧤 Parada","❌ Fallo"};
        for(String x:rs){
            Button b=btn(x);
            b.setOnClickListener(v->{
                if(x.contains("Gol")) recordAction("7m gol","7 metros","Gol");
                else if(x.contains("Parada")) recordAction("7m lanzamiento","7 metros","Parada");
                else recordAction("7m lanzamiento","7 metros","Fallo");
            });
            add(b);
        }
    }
    void chooseContraResult(){
        add(tv("Contraataque: ¿cómo ha terminado?",20));
        String[] rs={"⚽ Gol","❌ Fallo"};
        for(String x:rs){
            Button b=btn(x);
            String r=x.contains("Gol")?"Gol":"Fallo";
            b.setOnClickListener(v->recordAction("Contraataque","",r));
            add(b);
        }
    }
    void recordAction(String action,String zone,String result){
        int minute=currentMinute(); db.insertAction(currentMatch,selectedPlayer,minute,action,zone,result); db.recalc(currentMatch); selectedPlayer=null; pendingAction=null; pendingZone=null; ongoing();
    }

    void goalkeeperStep(){
        base("🥅 Portería · Partido");
        add(tv("Selecciona portera",20));
        Cursor c=db.q("SELECT id,nombre,dorsal FROM jugadores WHERE activo=1 AND lower(posicion) LIKE '%porter%' ORDER BY dorsal");
        while(c.moveToNext()){
            int id=c.getInt(0); Button b=btn("#"+c.getInt(2)+"  "+c.getString(1)); b.setOnClickListener(v->keeperZone(id)); add(b);
        } c.close();
        Button back=btn("↩️ Volver"); back.setOnClickListener(v->ongoing()); add(back);
    }
    void keeperZone(int playerId){
        base("🥅 Zona de lanzamiento");
        for(String z:ZONAS){Button b=btn("📍 "+z); b.setOnClickListener(v->keeperTipo(playerId,z)); add(b);}
    }
    void keeperTipo(int playerId,String zone){
        base("🥅 Tipo de lanzamiento");
        for(String t:TIPOS){Button b=btn(t); b.setOnClickListener(v->keeperDireccion(playerId,zone,t)); add(b);}
    }
    void keeperDireccion(int playerId,String zone,String tipo){
        base("🥅 Dirección");
        for(String dd:DIRECCIONES){Button b=btn(dd); b.setOnClickListener(v->keeperResult(playerId,zone,tipo,dd)); add(b);}
    }
    void keeperResult(int playerId,String zone,String tipo,String dir){
        base("🥅 Resultado");
        Button stop=btn("🧤 Parada"); stop.setOnClickListener(v->{insertKeeper(playerId,zone,tipo,dir,"Parada");ongoing();}); add(stop);
        Button goal=btn("⚽ Gol recibido"); goal.setOnClickListener(v->{insertKeeper(playerId,zone,tipo,dir,"Gol");ongoing();}); add(goal);
    }
    void insertKeeper(int playerId,String zone,String tipo,String dir,String result){
        int porteroId=db.ensurePortero(playerId); db.insertShot(currentMatch,porteroId,zone,tipo,dir,result,currentMinute()); db.recalc(currentMatch);
    }

    void players(){
        base("👥 Jugadoras");
        Button addb=btn("➕ Añadir jugadora"); addb.setOnClickListener(v->addPlayer()); add(addb); gap();
        Cursor c=db.q("SELECT id,nombre,dorsal,posicion,activo FROM jugadores ORDER BY dorsal,nombre");
        while(c.moveToNext()){
            final int id=c.getInt(0); final String nombre=c.getString(1); int dorsal=c.getInt(2); String pos=c.getString(3); final boolean activo=c.getInt(4)==1;
            String s="#"+dorsal+"  "+nombre+"\n"+(pos==null?"":pos)+(activo?"":" · inactiva");

            LinearLayout card=new LinearLayout(this); card.setOrientation(LinearLayout.VERTICAL); card.setPadding(0,8,0,4);
            TextView t=tv(s,16); t.setOnClickListener(v->playerStats(id)); card.addView(t);

            LinearLayout actionsRow=new LinearLayout(this); actionsRow.setOrientation(LinearLayout.HORIZONTAL);
            Button statsB=btn("📊 Stats"); statsB.setOnClickListener(v->playerStats(id));
            Button toggleB=btn(activo?"🔕 Desactivar":"↩️ Activar"); toggleB.setOnClickListener(v->{
                if(activo) db.deactivatePlayer(id); else db.activatePlayer(id);
                players();
            });
            Button delB=btn("🗑️ Borrar"); delB.setOnClickListener(v->confirmDeletePlayer(id,nombre));
            actionsRow.addView(statsB,new LinearLayout.LayoutParams(0,58,1));
            actionsRow.addView(toggleB,new LinearLayout.LayoutParams(0,58,1));
            actionsRow.addView(delB,new LinearLayout.LayoutParams(0,58,1));
            card.addView(actionsRow);

            View divider=new View(this); divider.setBackgroundColor(0xffdadfe3);
            content.addView(card,new LinearLayout.LayoutParams(-1,-2));
            content.addView(divider,new LinearLayout.LayoutParams(-1,2));
        } c.close();
        add(tv("La portería se registra dentro de «Partido en curso». No existe una plantilla de porteros separada.",14));
    }
    void confirmDeletePlayer(int id,String nombre){
        new AlertDialog.Builder(this).setTitle("Borrar jugadora")
            .setMessage("Se borrará definitivamente a "+nombre+" y todas sus acciones registradas en los partidos. Esta acción no se puede deshacer.\n\nSi prefieres conservar su historial, usa «Desactivar» en su lugar.")
            .setNegativeButton("Cancelar",null)
            .setPositiveButton("Borrar",(d,w)->{ db.deletePlayer(id); players(); })
            .show();
    }
    void addPlayer(){
        base("➕ Jugadora");
        EditText n=new EditText(this);n.setHint("Nombre");add(n); EditText d=new EditText(this);d.setHint("Dorsal");d.setInputType(2);add(d);
        EditText p=new EditText(this);p.setHint("Posición (ej. Central / Portera)");add(p);
        Button b=btn("💾 Guardar");b.setOnClickListener(v->{try{db.insertPlayer(n.getText().toString(),Integer.parseInt(d.getText().toString()),p.getText().toString());players();}catch(Exception e){toast("Revisa nombre y dorsal");}});add(b);
    }

    void stats(){
        base("📊 Estadísticas");
        Cursor c=db.q("SELECT id,equipo,rival,fecha,goles_favor,goles_contra FROM partidos ORDER BY fecha DESC,id DESC");
        while(c.moveToNext()){
            int id=c.getInt(0); Button b=btn(c.getString(1)+"  "+c.getInt(4)+" - "+c.getInt(5)+"  "+c.getString(2)); b.setOnClickListener(v->statsMatch(id));add(b);
        }c.close();
    }

    // ============================================================
    // ESTADÍSTICAS DE UN PARTIDO — en formato de tabla
    // ============================================================
    void statsMatch(int id){
        base("📊 Estadísticas");
        Cursor m=db.q("SELECT equipo,rival,goles_favor,goles_contra FROM partidos WHERE id="+id);
        if(m.moveToFirst())add(tv(m.getString(0)+"   "+m.getInt(2)+" - "+m.getInt(3)+"   "+m.getString(1),22));
        m.close();

        // -------- Jugadoras --------
        add(tv("👥 Estadísticas de jugadoras",19));
        List<String[]> filas=new ArrayList<>();
        int totGoles=0,totLanz=0,totAsist=0,totPerd=0,totRecup=0;
        Cursor c=db.q(
            "SELECT j.id,j.dorsal,j.nombre,j.posicion,"+
            "SUM(CASE WHEN a.accion='Gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Lanzamiento' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Lanzamiento' AND a.resultado='Gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Asistencia' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Pérdida' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Recuperación' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='1x1 ganado' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='1x1 perdido' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='7m gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='7m lanzamiento' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Exclusión' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN a.accion='Contraataque' AND a.resultado='Gol' THEN 1 ELSE 0 END)"+
            " FROM jugadores j LEFT JOIN acciones a ON a.jugador_id=j.id AND a.partido_id="+id+
            " WHERE j.activo=1 GROUP BY j.id ORDER BY j.dorsal"
        );
        while(c.moveToNext()){
            int golesDirectos=c.getInt(4), lanzTotal=c.getInt(5), lanzGol=c.getInt(6);
            int asist=c.getInt(7), perd=c.getInt(8), recup=c.getInt(9);
            int unoG=c.getInt(10), unoP=c.getInt(11);
            int m7g=c.getInt(12), m7lAttempt=c.getInt(13), exclus=c.getInt(14), contraG=c.getInt(15);

            // Un "Gol" también cuenta como lanzamiento (igual que en Python)
            int goles = golesDirectos + lanzGol;
            int lanz = golesDirectos + lanzTotal;
            int m7l = m7g + m7lAttempt;

            totGoles+=goles; totLanz+=lanz; totAsist+=asist; totPerd+=perd; totRecup+=recup;

            filas.add(new String[]{
                "#"+c.getInt(1)+" "+c.getString(2),
                c.getString(3)==null?"":c.getString(3),
                ""+goles, ""+lanz, pct(goles,lanz),
                ""+asist, ""+perd, ""+recup,
                ""+unoG, ""+unoP,
                ""+m7g, ""+m7l,
                ""+exclus, ""+contraG
            });
        }
        c.close();
        addTable(new String[]{"Jugadora","Pos.","Goles","Lanz.","% Lanz.","Asist.","Pérd.","Recup.","1x1+","1x1-","7m G","7m L","Exclus.","Contra G"}, filas);

        add(tv("📊 Resumen ofensivo",18));
        List<String[]> resumenOf=new ArrayList<>();
        resumenOf.add(new String[]{""+totGoles, ""+totLanz, ""+totAsist, ""+totPerd, ""+totRecup});
        addTable(new String[]{"Goles","Lanz.","Asist.","Pérdidas","Recup."}, resumenOf);

        // -------- Acciones registradas --------
        add(tv("📋 Acciones registradas",18));
        List<String[]> acciones=new ArrayList<>();
        Cursor ac=db.q("SELECT a.minuto,j.dorsal,j.nombre,a.accion,a.zona,a.resultado FROM acciones a LEFT JOIN jugadores j ON j.id=a.jugador_id WHERE a.partido_id="+id+" ORDER BY a.minuto,a.id");
        while(ac.moveToNext()){
            acciones.add(new String[]{
                ""+ac.getInt(0),
                "#"+ac.getInt(1)+" "+ac.getString(2),
                ac.getString(3),
                ac.getString(4)==null?"":ac.getString(4),
                ac.getString(5)==null?"":ac.getString(5)
            });
        }
        ac.close();
        if(acciones.isEmpty()) add(tv("Todavía no hay acciones registradas en este partido.",14));
        else addTable(new String[]{"Min","Jugadora","Acción","Zona","Resultado"}, acciones);

        // -------- Portería --------
        add(tv("🥅 Estadísticas de portería",19));
        List<String[]> shots=new ArrayList<>(); // porteroId, zona, tipo, direccion, resultado
        Cursor lp=db.q("SELECT portero_id,zona,tipo,direccion,resultado FROM lanzamientos_porteria WHERE partido_id="+id);
        while(lp.moveToNext()) shots.add(new String[]{lp.getString(0),lp.getString(1),lp.getString(2),lp.getString(3),lp.getString(4)});
        lp.close();

        int totalLanzP=shots.size();
        int totalParadas=0, totalGolesP=0;
        for(String[] s:shots){ if("Parada".equals(s[4]))totalParadas++; if("Gol".equals(s[4]))totalGolesP++; }
        List<String[]> resumenDef=new ArrayList<>();
        resumenDef.add(new String[]{""+totalLanzP, ""+totalParadas, ""+totalGolesP, pct(totalParadas,totalLanzP)});
        addTable(new String[]{"Lanzamientos","Paradas","Goles recibidos","% Paradas"}, resumenDef);

        add(tv("🥅 Estadísticas por portero/a",18));
        List<String[]> filasPort=new ArrayList<>();
        Cursor pk=db.q("SELECT DISTINCT p.id,p.nombre,p.dorsal FROM lanzamientos_porteria lp INNER JOIN porteros p ON p.id=lp.portero_id WHERE lp.partido_id="+id+" ORDER BY p.dorsal");
        while(pk.moveToNext()){
            String pid=""+pk.getInt(0);
            int t=0,par=0,gol=0;
            for(String[] s:shots){ if(pid.equals(s[0])){ t++; if("Parada".equals(s[4]))par++; if("Gol".equals(s[4]))gol++; } }
            filasPort.add(new String[]{"#"+pk.getInt(2)+" "+pk.getString(1), ""+t, ""+par, ""+gol, pct(par,t)});
        }
        pk.close();
        if(filasPort.isEmpty()) add(tv("Todavía no hay estadísticas de portería para este partido.",14));
        else addTable(new String[]{"Portero/a","Lanzamientos","Paradas","Goles","% Paradas"}, filasPort);

        add(tv("📍 Lanzamientos por zona",18));
        addTable(new String[]{"Zona","Lanzamientos","Paradas","Goles","% Paradas"}, byCategory(shots,1,ZONAS));

        add(tv("🎯 Lanzamientos por tipo",18));
        addTable(new String[]{"Tipo","Lanzamientos","Paradas","Goles","% Paradas"}, byCategory(shots,2,TIPOS));

        add(tv("↗️ Lanzamientos por dirección",18));
        addTable(new String[]{"Dirección","Lanzamientos","Paradas","Goles","% Paradas"}, byCategory(shots,3,DIRECCIONES));

        if(totalLanzP==0) add(tv("Este partido todavía no tiene lanzamientos de portería registrados.",14));
    }

    // shots: [porteroId, zona, tipo, direccion, resultado] — idx 1..3 selecciona la categoría a agrupar
    List<String[]> byCategory(List<String[]> shots, int idx, String[] categorias){
        List<String[]> rows=new ArrayList<>();
        for(String cat:categorias){
            int total=0, paradas=0, goles=0;
            for(String[] s:shots){
                if(cat.equals(s[idx])){
                    total++;
                    if("Parada".equals(s[4])) paradas++;
                    if("Gol".equals(s[4])) goles++;
                }
            }
            rows.add(new String[]{cat, ""+total, ""+paradas, ""+goles, pct(paradas,total)});
        }
        return rows;
    }

    // ============================================================
    // ESTADÍSTICAS DE UNA JUGADORA (extra: histórico completo)
    // ============================================================
    void playerStats(int playerId){
        Cursor p=db.q("SELECT nombre,dorsal,posicion,activo FROM jugadores WHERE id="+playerId);
        String name="",pos=""; int dorsal=0; boolean activo=true;
        if(p.moveToFirst()){name=p.getString(0);dorsal=p.getInt(1);pos=p.getString(2);activo=p.getInt(3)==1;} p.close();
        base("👤 #"+dorsal+" "+name);
        add(tv((pos==null?"":pos)+(activo?"":"  ·  inactiva"),16));

        Cursor c=db.q(
            "SELECT "+
            "SUM(CASE WHEN accion='Gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Lanzamiento' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Lanzamiento' AND resultado='Gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Asistencia' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Pérdida' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Recuperación' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='1x1 ganado' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='1x1 perdido' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='7m gol' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='7m lanzamiento' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Exclusión' THEN 1 ELSE 0 END),"+
            "SUM(CASE WHEN accion='Contraataque' AND resultado='Gol' THEN 1 ELSE 0 END),"+
            "COUNT(DISTINCT partido_id)"+
            " FROM acciones WHERE jugador_id="+playerId
        );
        List<String[]> totales=new ArrayList<>();
        int partidosJugados=0;
        if(c.moveToFirst()){
            int golesDirectos=c.getInt(0), lanzTotal=c.getInt(1), lanzGol=c.getInt(2);
            int asist=c.getInt(3), perd=c.getInt(4), recup=c.getInt(5);
            int unoG=c.getInt(6), unoP=c.getInt(7);
            int m7g=c.getInt(8), m7lAttempt=c.getInt(9), exclus=c.getInt(10), contraG=c.getInt(11);
            partidosJugados=c.getInt(12);
            int goles=golesDirectos+lanzGol, lanz=golesDirectos+lanzTotal, m7l=m7g+m7lAttempt;
            totales.add(new String[]{
                ""+partidosJugados, ""+goles, ""+lanz, pct(goles,lanz),
                ""+asist, ""+perd, ""+recup, ""+unoG, ""+unoP,
                ""+m7g, ""+m7l, ""+exclus, ""+contraG
            });
        }
        c.close();
        add(tv("📊 Totales (todos los partidos)",19));
        addTable(new String[]{"Partidos","Goles","Lanz.","% Lanz.","Asist.","Pérd.","Recup.","1x1+","1x1-","7m G","7m L","Exclus.","Contra G"}, totales);

        add(tv("📋 Estadísticas por partido",19));
        List<String[]> porPartido=new ArrayList<>();
        Cursor pm=db.q("SELECT id,rival,fecha FROM partidos ORDER BY fecha DESC,id DESC");
        while(pm.moveToNext()){
            int mid=pm.getInt(0); String rival=pm.getString(1); String fecha=pm.getString(2);
            Cursor cm=db.q(
                "SELECT "+
                "SUM(CASE WHEN accion='Gol' THEN 1 ELSE 0 END),"+
                "SUM(CASE WHEN accion='Lanzamiento' THEN 1 ELSE 0 END),"+
                "SUM(CASE WHEN accion='Lanzamiento' AND resultado='Gol' THEN 1 ELSE 0 END),"+
                "SUM(CASE WHEN accion='Asistencia' THEN 1 ELSE 0 END),"+
                "COUNT(*)"+
                " FROM acciones WHERE jugador_id="+playerId+" AND partido_id="+mid
            );
            if(cm.moveToFirst()){
                int totAcc=cm.getInt(4);
                if(totAcc>0){
                    int golesDirectos=cm.getInt(0), lanzTotal=cm.getInt(1), lanzGol=cm.getInt(2), asist=cm.getInt(3);
                    int goles=golesDirectos+lanzGol, lanz=golesDirectos+lanzTotal;
                    porPartido.add(new String[]{rival, fecha, ""+goles, ""+lanz, ""+asist});
                }
            }
            cm.close();
        }
        pm.close();
        if(porPartido.isEmpty()) add(tv("Esta jugadora todavía no tiene acciones registradas.",14));
        else addTable(new String[]{"Rival","Fecha","Goles","Lanz.","Asist."}, porPartido);

        // Si juega de portera, mostrar también sus estadísticas de portería acumuladas
        if(pos!=null && pos.toLowerCase(Locale.getDefault()).contains("porter")){
            Cursor pid=db.q("SELECT id FROM porteros WHERE lower(nombre)=lower(?) AND dorsal=?", new String[]{name, ""+dorsal});
            List<String[]> shots=new ArrayList<>();
            while(pid.moveToNext()){
                Cursor lp=db.q("SELECT zona,tipo,direccion,resultado FROM lanzamientos_porteria WHERE portero_id="+pid.getInt(0));
                while(lp.moveToNext()) shots.add(new String[]{null,lp.getString(0),lp.getString(1),lp.getString(2),lp.getString(3)});
                lp.close();
            }
            pid.close();
            if(!shots.isEmpty()){
                int t=shots.size(), par=0, gol=0;
                for(String[] s:shots){ if("Parada".equals(s[4]))par++; if("Gol".equals(s[4]))gol++; }
                add(tv("🥅 Portería (todos los partidos)",19));
                List<String[]> rowP=new ArrayList<>();
                rowP.add(new String[]{""+t, ""+par, ""+gol, pct(par,t)});
                addTable(new String[]{"Lanzamientos","Paradas","Goles","% Paradas"}, rowP);
                add(tv("📍 Por zona",17));
                addTable(new String[]{"Zona","Lanzamientos","Paradas","Goles","% Paradas"}, byCategory(shots,1,ZONAS));
            }
        }
    }

    void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}

    static class DB extends SQLiteOpenHelper {
        static final String NAME="balonmano.db";
        Context ctx;
        DB(Context c){super(c,NAME,null,1);ctx=c;copyIfNeeded();}
        void copyIfNeeded(){
            File f=ctx.getDatabasePath(NAME); if(f.exists())return; f.getParentFile().mkdirs();
            try(InputStream in=ctx.getAssets().open(NAME);OutputStream out=new FileOutputStream(f)){byte[] b=new byte[8192];int n;while((n=in.read(b))>0)out.write(b,0,n);}catch(Exception e){throw new RuntimeException(e);}
        }
        public void onCreate(SQLiteDatabase d){}
        public void onUpgrade(SQLiteDatabase d,int o,int n){}
        Cursor q(String sql){return getReadableDatabase().rawQuery(sql,null);}
        int insertMatch(String e,String r,String f,String comp){ContentValues v=new ContentValues();v.put("equipo",e);v.put("rival",r);v.put("fecha",f);v.put("competicion",comp);return (int)getWritableDatabase().insert("partidos",null,v);}
        void insertPlayer(String n,int d,String p){ContentValues v=new ContentValues();v.put("nombre",n);v.put("dorsal",d);v.put("posicion",p);v.put("activo",1);getWritableDatabase().insert("jugadores",null,v);}
        void deactivatePlayer(int id){ContentValues v=new ContentValues();v.put("activo",0);getWritableDatabase().update("jugadores",v,"id=?",new String[]{""+id});}
        void activatePlayer(int id){ContentValues v=new ContentValues();v.put("activo",1);getWritableDatabase().update("jugadores",v,"id=?",new String[]{""+id});}
        void deletePlayer(int id){
            SQLiteDatabase d=getWritableDatabase();
            d.beginTransaction();
            try{
                d.delete("acciones","jugador_id=?",new String[]{""+id});
                d.delete("estadisticas_jugadores","jugador_id=?",new String[]{""+id});
                d.delete("estadisticas_defensa","jugador_id=?",new String[]{""+id});
                d.delete("lanzamientos_jugadores","jugador_id=?",new String[]{""+id});
                d.delete("jugadores","id=?",new String[]{""+id});
                d.setTransactionSuccessful();
            } finally { d.endTransaction(); }
        }
        void insertAction(int match,int player,int min,String act,String zone,String res){ContentValues v=new ContentValues();v.put("partido_id",match);v.put("jugador_id",player);v.put("minuto",min);v.put("accion",act);v.put("zona",zone);v.put("resultado",res);v.put("observacion","");getWritableDatabase().insert("acciones",null,v);}
        void insertShot(int match,int keeper,String zone,String type,String dir,String res,int min){ContentValues v=new ContentValues();v.put("partido_id",match);v.put("portero_id",keeper);v.put("zona",zone);v.put("tipo",type);v.put("direccion",dir);v.put("resultado",res);v.put("minuto",min);v.put("observacion","");getWritableDatabase().insert("lanzamientos_porteria",null,v);}
        int ensurePortero(int playerId){Cursor c=q("SELECT nombre,dorsal FROM jugadores WHERE id="+playerId);String n="";int d=0;if(c.moveToFirst()){n=c.getString(0);d=c.getInt(1);}c.close();Cursor x=q("SELECT id FROM porteros WHERE lower(nombre)=lower(?) AND dorsal=? AND activo=1",new String[]{n,""+d});if(x.moveToFirst()){int id=x.getInt(0);x.close();return id;}x.close();ContentValues v=new ContentValues();v.put("nombre",n);v.put("dorsal",d);v.put("activo",1);return (int)getWritableDatabase().insert("porteros",null,v);}
        Cursor q(String sql,String[] args){return getReadableDatabase().rawQuery(sql,args);}
        void deleteAction(int id){getWritableDatabase().delete("acciones","id=?",new String[]{""+id});}
        void deleteShot(int id){getWritableDatabase().delete("lanzamientos_porteria","id=?",new String[]{""+id});}
        void deleteMatch(int id){
            SQLiteDatabase d=getWritableDatabase();d.delete("acciones","partido_id=?",new String[]{""+id});d.delete("lanzamientos_porteria","partido_id=?",new String[]{""+id});d.delete("estadisticas_jugadores","partido_id=?",new String[]{""+id});d.delete("estadisticas_defensa","partido_id=?",new String[]{""+id});d.delete("estadisticas_porteros","partido_id=?",new String[]{""+id});d.delete("lanzamientos_jugadores","partido_id=?",new String[]{""+id});d.delete("partidos","id=?",new String[]{""+id});
        }
        // Recalcula el marcador exactamente igual que recalcular_marcador() en Python:
        // un lanzamiento que termina en gol TAMBIÉN suma al marcador.
        void recalc(int id){
            SQLiteDatabase d=getWritableDatabase();
            Cursor a=d.rawQuery(
                "SELECT COUNT(*) FROM acciones WHERE partido_id=? AND ("+
                "accion='Gol' OR (accion='Lanzamiento' AND resultado='Gol') OR "+
                "accion='7m gol' OR (accion='Contraataque' AND resultado='Gol'))",
                new String[]{""+id});
            int gf=0;if(a.moveToFirst())gf=a.getInt(0);a.close();
            Cursor b=d.rawQuery("SELECT COUNT(*) FROM lanzamientos_porteria WHERE partido_id=? AND resultado='Gol'",new String[]{""+id});int gc=0;if(b.moveToFirst())gc=b.getInt(0);b.close();
            ContentValues v=new ContentValues();v.put("goles_favor",gf);v.put("goles_contra",gc);d.update("partidos",v,"id=?",new String[]{""+id});
        }
    }
}
