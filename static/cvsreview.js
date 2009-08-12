function loadLogMessage(change_id) {
   $("#shortlog"+change_id).toggle();
   $("#longlog"+change_id).toggle();
   $("#longlogswitch"+change_id).toggle();
};

function switchtime(change_id) {
   $("#time"+change_id).toggle();
   $("#timenice"+change_id).toggle();
}

function showdiff(show, change_id) { 
   if (show) {
      $("#diffview"+change_id).load("/diff/"+change_id+"/html");
   }
   $("#showdiff"+change_id).toggle();
   $("#hidediff"+change_id).toggle();
   $("#bhidediff"+change_id).toggle();
   $("#diffview"+change_id).toggle();
}

function togglemodlist(cat_id) {
   $("#modulelist_cat_"+cat_id).toggle();
   $("#imgarrow_"+cat_id).toggle();
   $("#imgtriangle_"+cat_id).toggle();
   if ($("#modulelist_cat_"+cat_id).css('display') == 'none') {
      $.cookie('cat_'+cat_id, 'n', {path:'/'});
   } else {
      $.cookie('cat_'+cat_id, 'y', {path:'/'});
   }
}

function showlogin() {
   $("#loginform").toggle();
}

function showaddmodule() {
   $("#addmoduleform").toggle();
   $("#addmoduleerror").text("")
   $("#addmoduleresult").text("");
}

function addmodule() {
   name = $("#addmodulename").val();
   path = $("#addmodulepath").val();
   category = $("#addmodulecat").val();
   $.getJSON("/addmodule", {'name':name, 'path':path, 'cat':category},
      function(json){
         if (json.status == 'ok') {
            errormessage = "";
         } else if (json.status == 'pathexist') {
            errormessage = "This module is already added.";
         } else if (json.status == 'nameexist') {
            errormessage = "This name is already used.";
         } else if (json.status == 'notexist') {
            errormessage = "This module does not exist.";
         } else if (json.status == 'nameinvalid') {
            errormessage = "This name is not valid.";
         } else if (json.status == 'pathinvalid') {
            errormessage = "This path is not valid.";
         } else if (json.status == 'catinvalid') {
            errormessage = "This category is not valid.";
         } else {
            errormessage = "CBASE_ERR_INTERNAL";
         }
         $("#addmoduleerror").text(errormessage)

         if (json.status == 'ok') { 
            $("#addmoduleresult").text("OK");
            $("#addmoduleform").toggle();
            location.reload(); 
         }
      }
   );
}

function login() {
  username = $("#username").val();
  $.getJSON("/login", 
     {'username':username},
     function(json){
        if (json.status == 'ok') {
           location.reload(); 
        } else {
           //display error
        }
     }
  )
}

/*
vim:set ts=3 sw=3 nowrap et ai:  
*/
