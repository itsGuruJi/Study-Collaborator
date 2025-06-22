from . forms import *
from django.core.checks import messages
from django.shortcuts import redirect, render
from django import contrib
from django.contrib import messages # for posting messages, fixed forbidden csrf token issue
from django.views import generic
import wikipedia #used in Wikipedia
import random
from django.contrib.auth.decorators import login_required
from youtubesearchpython import VideosSearch # for playing Youtube videos
import requests # used in books for searching
from django.conf import settings

# Create your views here.
def home(request):
    return render(request, 'dashboard/home.html')

class NotesDetailView(generic.DetailView):
    model = Notes

@login_required
def notes(request):
    """
    This function is used to create, update, delete, and manage notes while studying.
    """
    if request.method == "POST":
        form = NoteDescForm(request.POST)
        if form.is_valid():
            Notes.objects.create(
                title=request.POST['title'],
                user=request.user,
                desc=request.POST['desc'],
            )
            messages.success(request, "Your note has been saved successfully!")
            return redirect('notes')  # Redirect to prevent form resubmission
    else:
        form = NoteDescForm()
    
    # Fetch notes for the logged-in user
    notes = Notes.objects.filter(user=request.user)
    # Fetch all users for sharing functionality
    all_users = User.objects.all()
    
    context = {
        'notes': notes,
        'form': form,
        'all_users': all_users,
    }
    return render(request, 'dashboard/notes.html', context)

@login_required
def delete_note(request, primaryKey=None):
    # The note associated with this specific primary key (PK) will be delete
    Notes.objects.get(id = primaryKey).delete()
    return redirect("notes")

def shareNote(request, primaryKey=None):
    # HOW to share note to another user's session?
    obj = request.POST.copy()
    shared_user = User.objects.get(pk = obj['shared_user'])
    note = Notes.objects.get(id = primaryKey)
    obj['title'] = note.title
    obj['desc'] = note.desc

    form = NoteDescForm(obj)
    if(form.is_valid()):
        print(" Sending to user: ", shared_user)
        notes = Notes(
                    title = obj['title'],
                    user = shared_user,
                    desc = obj['desc'],
                    )
        notes.save()
        messages.success(request, f"Saved the notes to {shared_user} successfully")
    else:
        messages.success(request, f"Could not save the notes to {shared_user}")
        print("FAILED SHARING")
    return redirect("notes")

@login_required
def homework(request):
    if request.method == "POST":
        hwForm = HwForm(request.POST)
        if hwForm.is_valid():
            try:
                done = request.POST.get('is_finished', 'off') == 'on'
            except KeyError:
                done = False

            homeworks = Homework(
                user=request.user,
                title=request.POST['title'],
                subject=request.POST['subject'],
                due=request.POST['due'],
                desc=request.POST['desc'],
                is_finished=done,
            )
            homeworks.save()
            messages.success(request, f"Saved homework from {request.user.username}!")

            # Redirect after successfully saving homework
            return redirect('homework')  # Prevents form resubmission

    else:
        hwForm = HwForm()

    homework = Homework.objects.filter(user=request.user)
    hw_done = not homework.exists()

    context = {
        'homeworks': homework,
        'hw_done': hw_done,
        'form': hwForm,
    }
    return render(request, 'dashboard/homework.html', context)



@login_required
def update_homework(request, primaryKey = None):
    print("\n\nI AM here \n\n")
    hw = Homework.objects.get(id = primaryKey)    # updating in DB
    if(hw.is_finished == True):
        hw.is_finished = False
    else:
        hw.is_finished = True
    hw.save()
    return redirect('homework')


@login_required
def delete_homework(request, primaryKey = None):
    Homework.objects.get(id = primaryKey).delete()  # deleting from Database
    return redirect('homework')

def youtube(request):
    if(request.method == "POST"):
        YoutubeForm = DashboardForm(request.POST)
        text = request.POST['text']
        video = VideosSearch(text, limit = 300)  # serch built-in function!
        res = []
        for i in video.result()['result']:
            res_dict = {
            'input': text,
            'title' : i['title'],
            'duration' : i['duration'],
            'thumbnail' : i['thumbnails'][0]['url'],
            'link' : i['link'],
            'views' : i['viewCount']['short'],
            'published' : i['publishedTime'],
            'channel' : i['channel']['name'],
            }
            # some vids don't have description
            description = ''
            if( i['descriptionSnippet']):
                for j in i['descriptionSnippet']:
                    description += j['text']
            res_dict['description'] = description
            res.append(res_dict)
            context = {
                'form': YoutubeForm,
                'results': res,
            }
        return render(request, 'dashboard/youtube.html', context)
    else:
        YoutubeForm = DashboardForm()

    context = {'form': YoutubeForm}
    return render(request, "dashboard/youtube.html", context)

@login_required
def todo(request):
    if request.method == "POST":
        form = TodoForm(request.POST)
        if form.is_valid():
            try:
                done = request.POST.get('is_finished', '') == 'on'
            except KeyError:
                done = False
            todos = Todo(
                user=request.user,
                title=request.POST['title'],
                desc=request.POST['desc'],
                is_finished=done
            )
            todos.save()
            messages.success(request, f"Saved todo for {request.user.username}!")
            # Redirect to prevent duplicate submissions
            return redirect('todo')  # Replace 'todo' with the name of your URL pattern for this view

    else:
        form = TodoForm()

    todo = Todo.objects.filter(user=request.user)
    todos_done = not todo.exists()

    context = {
        'todos': todo,
        'form': form,
        'todos_done': todos_done,
    }
    return render(request, "dashboard/todo.html", context)
@login_required
def update_todo(request, primaryKey = None):
    task = Todo.objects.get(id = primaryKey)    # updating in DB
    if(task.is_finished == True):
        task.is_finished = False
    else:
        task.is_finished = True
    task.save()
    return redirect('todo')


@login_required
def delete_todo(request, primaryKey = None):
    Todo.objects.get(id = primaryKey).delete()  # deleting from DB
    return redirect('todo')
def books(request):
    if(request.method == "POST"):
        form = DashboardForm(request.POST)
        text = request.POST['text']
        # url = "https://www.googleapis.com/books/v1/volumes?q=" + text
        api_key = settings.GOOGLE_BOOKS_API_KEY
        url = f"https://www.googleapis.com/books/v1/volumes?q={text}&key={api_key}"
        r = requests.get(url)
        ans = r.json()
        res = []
        for i in range(10):
            volume_info = ans['items'][i]['volumeInfo']
            image_links = volume_info.get('imageLinks', {})
            res_dict = {
                'title': volume_info['title'],
                'subtitle': volume_info.get('subtitle'),
                'desc': volume_info.get('description'),
                'count': volume_info.get('pageCount'),
                'categories': volume_info.get('categories'),
                'rating': volume_info.get('pageRating'),
                'thumbnail': image_links.get('thumbnail', 'default_thumbnail_url'),  # Fallback thumbnail URL
                'preview': volume_info.get('previewLink'),
            }
            res.append(res_dict)

        context = {
            'form': form,
            'results': res,
        }
        return render(request, 'dashboard/books.html', context)
    else:
        form = DashboardForm()

    context = {'form': form}
    return render(request, "dashboard/books.html", context)


# def dictionary(request):
#     if(request.method == "POST"):
#         form = DashboardForm(request.POST)
#         text = request.POST['text']
#         url = "https://api.dictionaryapi.dev/api/v2/entries/en_US/" + text
#         print("\n\n\nURL = ", url)
#         r = requests.get(url)
#         ans = r.json()
#         res = []
#         # print("\n\n\nANS = ")
#         try:
#             # print("\n\n\nHIIIII = ")
#             phonetics = ans[0]['phonetics'][0]['text']
#             audio = ans[0]['phonetics'][0]['audio']
#             definition = ans[0]['meanings'][0]['definitions'][0]['definition']
#             example = ans[0]['meanings'][0]['definitions'][0]['example']
#             synonyms = ans[0]['meanings'][0]['definitions'][0]['synonyms']
#             context = {
#                 'form': form,
#                 'input': text,
#                 'phonetics': phonetics,
#                 'audio': audio,
#                 'definition': definition,
#                 'example': example,
#                 'synonyms': synonyms,
#             }
#             print("CONTEXT inside TRY\n\n", context)
#         except:
#             context = {
#                 'form': form,
#                 'input': '',
#             }
#             messages.success(request, f"Word does not exist in dictionary! Try again.")
#         return render(request, 'dashboard/dictionary.html', context)
#     else:
#         form = DashboardForm()
#         context = {'form':form}
#     print("\n\n\ncontext = ", context)

#     return render(request, 'dashboard/dictionary.html', context)
import requests
from django.shortcuts import render
from django.contrib import messages
from .forms import DashboardForm  # Assuming you have this form defined

def dictionary(request):
    if request.method == "POST":
        form = DashboardForm(request.POST)
        text = request.POST.get('text', '').strip()  # Safely get 'text' from POST data
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en_US/{text}"
        print(f"URL = {url}")
        try:
            r = requests.get(url)
            r.raise_for_status()  # Raise HTTPError for bad status codes
            ans = r.json()
            print("API Response:", ans)  # Debugging

            phonetics = ans[0].get('phonetics', [{}])[0].get('text', 'N/A')
            audio = ans[0].get('phonetics', [{}])[0].get('audio', '')
            definition = ans[0]['meanings'][0]['definitions'][0].get('definition', 'Definition not found.')
            example = ans[0]['meanings'][0]['definitions'][0].get('example', 'No example available.')
            synonyms = ans[0]['meanings'][0]['definitions'][0].get('synonyms', [])

            context = {
                'form': form,
                'input': text,
                'phonetics': phonetics,
                'audio': audio,
                'definition': definition,
                'example': example,
                'synonyms': synonyms,
            }
        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e}")
            messages.error(request, "There was a problem with the dictionary API.")
            context = {'form': form, 'input': ''}
        except (IndexError, KeyError) as e:
            print(f"Data Parsing Error: {e}")
            messages.error(request, "Word not found in dictionary.")
            context = {'form': form, 'input': ''}
        return render(request, 'dashboard/dictionary.html', context)
    else:
        form = DashboardForm()
        context = {'form': form}
    return render(request, 'dashboard/dictionary.html', context)


def wiki(request):
    form = DashboardForm()
    context = {'form': form}

    if request.method == "POST":
        text = request.POST.get('text', '').strip()
        
        if not text:  # Handle empty input
            messages.error(request, "Please enter a valid search term.")
            return render(request, 'dashboard/wiki.html', context)

        form = DashboardForm(request.POST)

        try:
            # Attempt to get the Wikipedia page
            p = wikipedia.page(text, auto_suggest=False)
            context.update({
                'title': p.title,
                'details': p.summary,
                'link': p.url,
            })

        except wikipedia.DisambiguationError as e:
            # Handle disambiguation by showing the user options
            context.update({
                'title': "Disambiguation Error",
                'details': f"The term '{text}' is ambiguous. Here are some suggestions:",
                'options': e.options,
            })
        
        except wikipedia.PageError:
            # Handle page not found error
            messages.error(request, f"No Wikipedia page found for '{text}'. Please try another term.")
        
        except Exception as ex:
            # Handle unexpected errors
            messages.error(request, f"An error occurred: {str(ex)}")

        return render(request, 'dashboard/wiki.html', context)

    return render(request, 'dashboard/wiki.html', context)

def conversion(request):
    if(request.method == "POST"):
        form = ConversationForm(request.POST)
        if request.POST['measurement'] == 'length':
            measureForm = LengthConversion()
            context = {
                'form': form,
                'measureForm': measureForm,
                'input': True,
            }
            if('input' in request.POST):
                first = request.POST['measure1']
                second = request.POST['measure2']
                input = request.POST['input']
                ans = ''
                if input and int(input) >= 0:
                    if(first == 'yard' and second == 'foot'):
                        ans = f'{input} yard = {int(input)*3} foot'
                    elif(first == 'foot' and second == 'yard'):
                        ans = f'{input} foot = {int(input)/3} yard'
                    else:
                        print("\n\n Invalid input \n\n")
                context = {
                    'form': form,
                    'measureForm': measureForm,
                    'input': True,
                    'ans': ans,
                }
                print("ANS: ", ans, "\n----------\n\n")
        if request.POST['measurement'] == 'mass':
            measureForm = MassConversion()
            context = {
                'form': form,
                'measureForm': measureForm,
                'input': True,
            }
            if('input' in request.POST):
                first = request.POST['measure1']
                second = request.POST['measure2']
                input = request.POST['input']
                ans = ''
                if input and int(input) >= 0:
                    if(first == 'pound' and second == 'kg'):
                        ans = f'{input} pound = {int(input)*0.453592} kg'
                    elif(first == 'kg' and second == 'pound'):
                        ans = f'{input} kg = {int(input)*2.20462} pound'
                    else:
                        print("\n\n Invalid input \n\n")
                context = {
                    'form': form,
                    'measureForm': measureForm,
                    'input': True,
                    'ans': ans,
                }
                print("ANS: ", ans, "\n----------\n\n")
    else:
        form = ConversationForm()
        context = {
            'form': form,
            'input': False
        }
    print(" \ncontext: ", context, "\n\n")
    return render(request, 'dashboard/conversion.html', context)

def register(request):
    if(request.method == "POST"):
        form = UserRegForm(request.POST)
        if(form.is_valid()):
            user_ = form.cleaned_data.get('username')
            messages.success(request, f"Account Created for {user_}!")
            form.save()
            return redirect("signin")
    else:
        form = UserRegForm()
    context ={
        'form': form
    }
    return render(request, "dashboard/register.html", context)

@login_required
def profile(request):
    homeworks = Homework.objects.filter(is_finished = False, user = request.user)
    todos = Todo.objects.filter(is_finished = False, user = request.user)
    if(len(homeworks)==0):
        hw_done = True
    else:
        hw_done = False
    if(len(todos)==0):
        todos_done = True
    else:
        todos_done = False
    context = {
        'hw_done' : hw_done,
        'todos_done' : todos_done,
        'homeworks' : homeworks,
        'todos' : todos,
    }
    return render(request, "dashboard/profile.html", context)

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.http import HttpResponseNotAllowed
def signout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')  # Redirect to home or another page after logout
    else:
        return HttpResponseNotAllowed(['POST'])