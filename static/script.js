var debugging = new Map(); //Keys: response,button


// #########################
// FROM: https://stackoverflow.com/questions/400212/how-do-i-copy-to-the-clipboard-in-javascript
function fallbackCopyTextToClipboard(text) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    
    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
  
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
  
    try {
        var successful = document.execCommand('copy');
        var msg = successful ? 'successful' : 'unsuccessful';
        debugging.set('clipboardCopying', 'Fallback: Copying text command was ' + msg);
    } catch (err) {
        debugging.set('clipboardCopying', 'Fallback: Oops, unable to copy');
        debugging.set('clipboardCopyingErr', err);
    }
    document.body.removeChild(textArea);
}

function copyTextToClipboard(text) {
    if (!navigator.clipboard) {
        fallbackCopyTextToClipboard(text);
        return;
    }
    navigator.clipboard.writeText(text).then(function() {
        debugging.set('clipboardCopying', 'Async: Copying to clipboard was successful!');
    }, function(err) {
        debugging.set('clipboardCopying', 'Async: Could not copy text:');
        debugging.set('clipboardCopyingErr', err);
    });
}

// #########################

function copyCollectionToClipboard(text) {
    // Use JS builtin selector, jquery selector returns an array, hence the inability to access the property value
    // If you want to use jquery, select the item inside the array first, then get its value.
    let header = document.getElementById('copyToClipboardHeader').value;
    copyTextToClipboard(header + '\n' + text);
}