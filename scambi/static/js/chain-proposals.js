(function () {
    'use strict';

    function getCard(cycleId) {
        return document.querySelector(`[data-ciclo-id="${cycleId}"]`);
    }

    function getButtons(card) {
        return card.querySelectorAll('.btn-mi-interessa');
    }

    function getCsrfToken() {
        const tokenElement = document.querySelector(
            'meta[name="polygonum-csrf-token"]'
        );
        return tokenElement ? tokenElement.content : '';
    }

    function setButtons(card, interested, disabled) {
        getButtons(card).forEach(function (button) {
            button.disabled = Boolean(disabled);
            button.classList.toggle('interested', interested);
            button.innerHTML = interested
                ? '<i class="fas fa-check me-1"></i>Interessato'
                : '<i class="fas fa-heart me-1"></i>Mi interessa';
        });
    }

    function setBusy(card) {
        getButtons(card).forEach(function (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Invio...';
        });
    }

    function updateBadges(card, data) {
        card.querySelectorAll('.badge-interessati').forEach(function (badge) {
            const countText = badge.querySelector('.count-text');
            if (countText) {
                countText.textContent = `${data.count_interessati}/${data.count_totale}`;
            }
            badge.style.display = 'inline-flex';
        });
    }

    window.renderChainSelection = function (card, selection) {
        const summary = card.querySelector('.active-chain-selection');
        const linesContainer = card.querySelector('.active-chain-selection-lines');
        const exchanges = selection && Array.isArray(selection.scambi)
            ? selection.scambi
            : [];
        if (!summary || !linesContainer || exchanges.length === 0) {
            if (summary) summary.hidden = true;
            return;
        }

        linesContainer.replaceChildren();
        exchanges.forEach(function (exchange) {
            const line = document.createElement('div');
            line.className = 'active-chain-selection-line';
            line.textContent = `${exchange.da_username} offre “${exchange.offerto_titolo}” a ${exchange.a_username}, che cerca “${exchange.richiesto_titolo}”`;
            linesContainer.appendChild(line);
        });
        summary.hidden = false;
    };

    function openSelection(card, button) {
        const modal = card.querySelector('.chain-selection-modal');
        if (!modal) {
            submitInterest(card, button, null);
            return;
        }
        card._pendingInterestButton = button;
        card.classList.add('selection-open');
        modal.hidden = false;
        document.body.classList.add('chain-selection-open');
        const firstSelect = modal.querySelector('select');
        if (firstSelect) firstSelect.focus();
    }

    window.chiudiSelezioneCatena = function (cycleId, clickEvent, fromBackdrop) {
        if (clickEvent) {
            clickEvent.preventDefault();
            clickEvent.stopPropagation();
            if (fromBackdrop && clickEvent.target !== clickEvent.currentTarget) return;
        }
        const card = getCard(cycleId);
        if (!card) return;
        const modal = card.querySelector('.chain-selection-modal');
        if (modal) modal.hidden = true;
        card.classList.remove('selection-open');
        card._pendingInterestButton = null;
        if (!document.querySelector('.chain-selection-modal:not([hidden])')) {
            document.body.classList.remove('chain-selection-open');
        }
    };

    window.confermaSelezioneCatena = function (cycleId, clickEvent) {
        if (clickEvent) {
            clickEvent.preventDefault();
            clickEvent.stopPropagation();
        }
        const card = getCard(cycleId);
        if (!card) return;
        const modal = card.querySelector('.chain-selection-modal');
        const selections = [];
        modal.querySelectorAll('.exchange-option-select').forEach(function (select) {
            const option = select.options[select.selectedIndex];
            selections.push({
                da_user: Number(select.dataset.daUser),
                a_user: Number(select.dataset.aUser),
                offerto_id: Number(option.dataset.offertoId),
                richiesto_id: Number(option.dataset.richiestoId),
            });
        });
        const button = card._pendingInterestButton || getButtons(card)[0];
        window.chiudiSelezioneCatena(cycleId, null, false);
        submitInterest(card, button, selections);
    };

    function updateChatBadge() {
        const desktopBadge = document.querySelector('#chatDropdown .badge');
        if (desktopBadge) {
            desktopBadge.textContent = (parseInt(desktopBadge.textContent, 10) || 0) + 1;
            desktopBadge.parentElement.style.display = '';
        }
        const mobileBadge = document.querySelector('.d-lg-none a[href*="lista_messaggi"] .badge');
        if (mobileBadge) {
            mobileBadge.textContent = (parseInt(mobileBadge.textContent, 10) || 0) + 1;
        }
    }

    async function submitInterest(card, button, selection) {
        const wasInterested = button.classList.contains('interested');
        setBusy(card);

        const body = selection === null
            ? {}
            : {selezione_annunci: selection};

        try {
            const response = await fetch(`/catene/proponi/${card.dataset.cicloId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(body),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                setButtons(card, wasInterested, false);
                if (data.requires_selection) {
                    openSelection(card, button);
                    return;
                }
                if (data.proposal_active === false) {
                    card.dataset.hasActiveProposal = 'false';
                    window.renderChainSelection(card, null);
                }
                alert('Errore: ' + (data.error || 'Impossibile registrare l’interesse.'));
                return;
            }

            updateBadges(card, data);
            card.dataset.hasActiveProposal = data.proposal_active ? 'true' : 'false';
            window.renderChainSelection(
                card,
                data.proposal_active ? data.selezione_annunci : null
            );

            if (data.action === 'added') {
                setButtons(card, true, false);
                if (data.tutti_interessati) {
                    if (data.chat_creata) {
                        updateChatBadge();
                        if (confirm('🎉 Tutti sono interessati! È stata creata una chat di gruppo. Vuoi andare alla chat?')) {
                            window.location.href = data.redirect_url;
                        }
                    } else {
                        alert('🎉 Tutti sono interessati! Verrà creata una chat di gruppo.');
                    }
                }
            } else {
                setButtons(card, false, false);
            }
        } catch (error) {
            console.error('Errore nel registrare l’interesse:', error);
            setButtons(card, wasInterested, false);
            alert('Errore nel registrare l’interesse. Riprova.');
        }
    }

    window.proponiCatena = function (cycleId, clickEvent) {
        if (clickEvent) {
            clickEvent.preventDefault();
            clickEvent.stopPropagation();
        }
        const button = clickEvent && clickEvent.currentTarget;
        const card = getCard(cycleId);
        if (!button || !card) return;

        const isInterested = button.classList.contains('interested');
        const needsSelection = card.dataset.requiresSelection === 'true';
        const proposalState = card.dataset.hasActiveProposal;
        if (!isInterested && needsSelection) {
            if (proposalState === 'false') {
                openSelection(card, button);
                return;
            }
            if (proposalState === 'unknown') {
                // Il server distingue atomicamente tra una proposta già attiva
                // (da accettare) e una nuova (per cui risponderà richiedendo la
                // scelta). Evita che un click molto rapido mostri il selettore
                // della combinazione sbagliata mentre lo stato è ancora in carico.
                submitInterest(card, button, null);
                return;
            }
        }
        submitInterest(card, button, null);
    };

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;
        const modal = document.querySelector('.chain-selection-modal:not([hidden])');
        if (!modal) return;
        const card = modal.closest('[data-ciclo-id]');
        window.chiudiSelezioneCatena(card.dataset.cicloId, event, false);
    });
})();
