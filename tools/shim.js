/* Read-only data layer for the public site: serves /data/<collection>.json through the same calls the app uses. */
(function(){
  var cache={};
  function load(name){
    if(!/^(clinics|prices|updates|reviews)$/.test(name))return Promise.resolve([]);
    if(!cache[name])cache[name]=fetch("/data/"+name+".json",{cache:"no-cache"}).then(function(r){return r.ok?r.json():[]}).catch(function(){return []});
    return cache[name];
  }
  function snap(rows){return{docs:rows.map(function(r){var id=r.id;return{id:id,data:function(){var o={};for(var k in r)if(k!=="id")o[k]=r[k];return o}}})}}
  function coll(name){
    var q={
      orderBy:function(){return q},limit:function(){return q},where:function(){return q},
      get:function(){return load(name).then(snap)},
      onSnapshot:function(ok,err){load(name).then(function(rows){ok(snap(rows))},function(e){if(err)err(e)});return function(){}},
      add:function(){return Promise.reject({code:"read_only"})}
    };
    return q;
  }
  var db={collection:coll,doc:function(){return{set:function(){return Promise.reject({code:"read_only"})},update:function(){return Promise.reject({code:"read_only"})},delete:function(){return Promise.reject({code:"read_only"})}}}};
  window.claude={use:function(n){return Promise.resolve(n==="db"?db:null)}};
})();
