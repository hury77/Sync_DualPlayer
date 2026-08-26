# RULES.md — Zasady pracy z kodem

## 0. Obowiązkowy odczyt przed każdą sesją
Przed podjęciem JAKIEGOKOLWIEK zadania związanego z kodem, agent MUSI:
1. Wykonać `cat RULES.md` i zacytować w odpowiedzi numer reguły,
   która jest najbardziej istotna dla nadchodzącego zadania.
2. Jeśli w danej sesji minęło więcej niż 5 wiadomości od ostatniego
   cytowania RULES.md — odczytać je ponownie przed kolejną edycją kodu.
Brak tego kroku = zadanie jest nieważne, niezależnie od jego jakości.

## 1. Przemyśl wszystko, zanim zaczniesz kodować
Sformułuj założenia, zapytaj w razie wątpliwości, porzuć wszelkie domysły.

## 2. Zacznij od najprostszego rozwiązania
Napisz tylko minimalny kod, który rozwiązuje problem, bez zbędnych abstrakcji.

## 3. Edytuj z chirurgiczną precyzją
Nie ruszaj kodu niezwiązanego z wymaganiami – każda zmieniona linijka jest powiązana z jasną specyfikacją.

## 4. Kieruj wykonaniem, kierując się celem
Zanim napiszesz pierwszą linijkę kodu, zamień niejasne instrukcje na weryfikowalne kryteria sukcesu.

## 5. Empiryczna weryfikacja to absolutny wymóg
Nigdy nie deklaruj ukończenia zadania na podstawie samego "poprawnego wyglądu" kodu. Agent ma kategoryczny zakaz zamykania zadania bez fizycznego uruchomienia kodu, weryfikacji logów i przetestowania zmodyfikowanej ścieżki w działającym środowisku. Zgadywanie wyników na sucho jest surowo zabronione.

## 6. Weryfikacja Nienaruszalnych Reguł (Guardrails Check)
Przed zatwierdzeniem jakiejkolwiek zmiany (zwłaszcza w obszarach takich jak czyszczenie, zapis plików czy routowanie), upewnij się, że modyfikacja nie łamie krytycznych reguł domenowych opisanych w plikach reguł danego projektu (jeśli takie istnieją). Brak regresji musi zostać potwierdzony, a nie tylko założony.

## 6a. Guardrails Check — status plików domenowych w tym projekcie
W tym repozytorium NIE ISTNIEJE plik SOUL.md ani żaden inny plik z regułami domenowymi. Agent nie ma próbować go odczytać, cytować ani zakładać jego istnienia w żadnym uzasadnieniu decyzji.
Jeśli w przyszłości powstanie taki plik (np. dot. retencji plików graficznych, separacji portów dev/prod), fakt ten zostanie explicit odnotowany w tym miejscu wraz z jego nazwą i ścieżką — do tego czasu Reguła 6 odnosi się wyłącznie do RULES.md.

## 7. Definicja "Gotowe" (Definition of Done)
Zadanie NIE jest zamknięte, dopóki agent nie przedstawi w odpowiedzi:
- [ ] dokładnej komendy/kroków użytych do weryfikacji (nie tylko "sprawdziłem"),
- [ ] surowego outputu/logu z tej weryfikacji (nie parafrazy),
- [ ] wyraźnego potwierdzenia, że testowano SCENARIUSZ UŻYTKOWNIKA (np. otwarcie zbudowanej `.dmg`, kliknięcie w UI), a nie tylko odpowiedź serwera (curl na root nie jest wystarczający).

Sformułowania typu "✅ Gotowe", "powinno działać", "zweryfikowałem lokalnie" bez dowodu są zabronione i traktowane jako naruszenie Reguły 5.

## 8. Refaktoryzacja = podwójna odpowiedzialność
Przy każdym rozbiciu pliku (np. `main.py` → serwisy) agent musi:
- wypisać listę WSZYSTKICH bloków kodu usuniętych z pliku źródłowego,
- dla każdego bloku wskazać, gdzie trafił (nowy plik) lub potwierdzić, że został intencjonalnie usunięty i dlaczego,
- na końcu wykonać `git diff --stat` między commitem przed i po zmianie, żeby liczba linii się zgadzała (nic "nie zgubiło się" w przepisywaniu).