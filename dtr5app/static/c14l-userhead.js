(function(){
    let template = document.createElement('template');
    template.innerHTML = `
        <style>
            #pics {
                background: white;
                display: block;
                height: 280px;
                margin: 32px 0;
                padding: 0;
                position: relative;
                overflow: hidden;
            }
            #pics div {
                background-position: center center;
                background-repeat: no-repeat;
                background-size: cover;
                border: 0;
                display: inline-block;
                height: 280px;
                left: 0;
                position: absolute;
                top: 0;
                transition: 0.5s ease-out;
                width: 280px;
            }
            #pics:hover div {
                box-shadow: 0 0 40px rgba(0,0,0,0.75);
            }
            #pics:hover div:nth-child(2) {
                left: calc(1 * 280px);
            }
            #pics:hover div:nth-child(3) {
                left: calc(2 * 280px);
            }
        </style>
        <div id="pics"></div>
    `;

    class C14LUserHead extends HTMLElement {

        constructor() {
            super();
            const templateContent = template.content.cloneNode(true);
            const picsEl = templateContent.getElementById('pics');

            this.getAttribute('pics').split(' ').filter(x => x).reverse().forEach(url => {
                const div = document.createElement('div');
                div.style.backgroundImage = `url(${url})`;
                picsEl.appendChild(div);
            });

            const shadowRoot = this.attachShadow({mode: 'open'});
            shadowRoot.appendChild(templateContent);
        }

        connectedCallback () {

        }

        disconnectedCallback () {

        }
    }

    window.customElements.define('c14l-userhead', C14LUserHead);
  })();