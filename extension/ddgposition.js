document.body.style.border = "5px solid red";


function download(file, text) {
  var element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8, ' + encodeURIComponent(text));
  element.setAttribute('download', file);
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

function timeout(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

var button = document.createElement('button');
button.innerHTML = "Download data for stock";
button.style.cssText = "position: absolute;z-index: 1000;margin-top: 50px;" 
button.className = "text-capitalize flex-grow-1 v-btn v-btn--is-elevated v-btn--has-bg theme--dark v-size--small"

button.onclick = async function() {
  var filename = document.querySelectorAll(".v-main__wrap .container.container--fluid span")[0].innerText.trim() + ".html"

  var links = document.querySelectorAll("main .v-tabs.v-tabs--centered.theme--dark.tabs .v-slide-group__wrapper a.v-tab")
  
  links[0].click()
  await timeout(1000)
  var income = document.querySelectorAll(".v-responsive.tblcontainer.d-inline-block.active table")[0].outerHTML

  links[1].click()
  await timeout(1000)
  var balance = document.querySelectorAll(".v-responsive.tblcontainer.d-inline-block.active table")[0].outerHTML

  links[2].click()
  await timeout(1000)
  var cash = document.querySelectorAll(".v-responsive.tblcontainer.d-inline-block.active table")[0].outerHTML

  links[3].click()
  await timeout(1000)
  var ratios = document.querySelectorAll(".v-responsive.tblcontainer.d-inline-block.active table")[0].outerHTML

  final = `${income}\n\n${balance}\n\n${cash}\n\n${ratios}`

  download(filename, final)
}

document.body.insertBefore(button, document.body.firstChild);
console.log("Button inserted")