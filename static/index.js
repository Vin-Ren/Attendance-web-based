
function setStatus(button) {
    debugging.set('button', button);
    $("#statusPlaceholder").attr("value", button.value);

}

$('#absenForm').submit(function(e){
    e.preventDefault();
    $.ajax({
        url: '/API/submission',
        type: 'post',
        data:$('#absenForm').serialize(),
        success:function(retval){
            $('#response-alert').remove();
            if (retval['success']) {
                let alert_type = (retval['alert_type'] !== undefined) ? retval['alert_type'] : 'success';
                var alertObj = `<div id="response-alert" class="alert alert-${alert_type}" role="alert">${retval['success_message']}</div>`;
                $('#responsePlaceholder').prepend(alertObj);
            }
            else {
                let alert_type = (retval['alert_type'] !== undefined) ? retval['alert_type'] : 'danger';
                var alertObj = `<div id="response-alert" class="alert alert-${alert_type}" role="alert">${retval['reason']}</div>`;
                $('#responsePlaceholder').prepend(alertObj);
            }
            debugging.set('response', retval)
        }
    });
});

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