$(document).ready(function() {
    var names = [];
    $.ajax({
        url: '/API/autocomplete_names',
        type: 'post',
        success: function(data){
            names=data['names'];
            setTimeout(function(){
                $( "#nameInput" ).autocomplete({
                    source: names,
                });
            }, 10); // timeout so it can be read?? idfk, what i do know though, is it works :D
    }});
});