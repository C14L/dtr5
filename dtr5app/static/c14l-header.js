(function(){
  let template = document.createElement('template');
  let linktpl = document.createElement('a');
  
  template.innerHTML = `
    <style>
      #header {
        background-color: rgba(0,82,128,1);
        /*
        background-color: rgba(0,82,128,0.56);
        #005280;
        #003B6F; reddit default color: #CEE3F8;
        border-bottom: 1px solid #5F99CF;
        box-shadow: 0 1px 3px rgba(0,0,0,0.28);
        */
        height: 64px;
        margin: 0; padding: 0;
        position: relative;
        white-space: nowrap;
      }
      #sitelogo {
        color: white;
        margin: 0; padding: 0;
        position: absolute; top: 0; left: 0;
      }
      #siteiconlink > img {
        border: 0;
        height: 48px;
        margin: 0; padding: 8px 16px;
        vertical-align: middle;
      }
      #sitenamelink {
        color: inherit; text-decoration: inherit;
        font-size: 1.5rem; line-height: 64px;
        font-weight: normal;
        letter-spacing: 0.3rem;
        text-shadow: 0 0 2px rgba(0,0,0,0.3);
        vertical-align: middle;
      }
      #sitelinks {
        font-size: 1rem; line-height: 56px;
        margin: 0; padding: 0;
        position: absolute; top: 0; right: 0;
      }
      #sitelinks c14l-hamburger {
        position: absolute; top: 0; right: 0;
        display: inline-block;
        color: white;
        padding-top: 14px;
        width: 64px; height: 50px;
      }
      #sitelinks .item {
        background-color: rgba(255,255,255,0);
        /*
        border-left: 1px solid rgba(255,255,255,0.28);
        */
        color: white;
        display: inline-block;
        margin: 0; padding: 4px 16px;
        position: relative;
        text-align: center;
        transition: 0.1s ease-out;
      }
      #sitelinks .item.settings:last-of-type {
        margin-right: 64px;
      }
      #sitelinks .item:hover {
        background-color: rgba(255,255,255,0.28);
        transition: 0.1s ease-out;
      }
      #sitelinks .item .number {
        background-color: rgab(0,0,0,0.56);
        border-radius: 50%;
        color: white;
        display: block;
        font-size: 1rem; line-height: 1.5rem;
        min-width: 1.5rem; height: 1.5rem;
        position: absolute; top: 0; right: 0;
        text-align: center;
        text-shadow: 1px 1px 1px black;
      }
      #sitelinks .item .icon, .site-links .sep {
        display: none;
      }
    </style>
    <header id="header">
      <div id="sitelogo">
        <a id="siteiconlink" href="/"><img src="" alt=""></a>
        <a id="sitenamelink" href="/"></a>
      </div>
      <div id="sitelinks">
      </div>
    </header>
  `;

  linktpl.innerHTML = `
    <a class="item" href="">
      <span class="text"></span>
      <span class="number"></span>
    </a>
  `;

  class C14LHeader extends HTMLElement {
      
    constructor() {
      super();
      const templateContent = template.content.cloneNode(true);
      const sitelinks = templateContent.getElementById('sitelinks');
      const siteiconlink = templateContent.getElementById('siteiconlink');
      const sitenamelink = templateContent.getElementById('sitenamelink');

      siteiconlink.querySelector('img').src = this.getAttribute('logo');
      siteiconlink.querySelector('img').alt = this.getAttribute('name');
      sitenamelink.innerHTML = this.getAttribute('name');

      for (let i=0; i<this.children.length; i++) {
        if (this.children[i].tagName == 'A') {
          let a = linktpl.cloneNode(true);
          a.setAttribute('href', this.children[i].getAttribute('href'));
          a.querySelector('.number').innerHTML = this.children[i].getAttribute('counter');
          a.querySelector('.text').innerHTML = this.children[i].innerHTML;
          sitelinks.appendChild(a);
        }
        else {
          sitelinks.appendChild(this.children[i]);
        }
      }
      this.innerHTML = '';
      const shadowRoot = this.attachShadow({mode: 'open'});
      shadowRoot.appendChild(templateContent);
    }
  
    connectedCallback () {

    }

    disconnectedCallback () {

    }
  }

  window.customElements.define('c14l-header', C14LHeader);
})();