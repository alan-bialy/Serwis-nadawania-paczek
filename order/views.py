import pickle
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# from django.http import request
from django.core.checks import messages
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, request, HttpResponse
from django.shortcuts import render, redirect, render_to_response
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic import RedirectView
from django.views.generic.edit import ModelFormMixin, FormMixin, FormView

from order.forms import FormParcelSize, AddressForm
from .models import Courier, PackPricing, PalletPricing, EnvelopePricing, Parcel, Order, SenderAddress, Address, \
    RecipientAddress, Profile
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView


class IndexView(generic.FormView):
    template_name = 'order/index.html'
    form_class = FormParcelSize

    def choose_pricing_col_and_ratio(self, type, weight, length, width, height):
        col_name_pricing = None
        if type == "koperta":  # Envelope Price
            col_name_pricing = 'up_to_1'
        elif type == "paczka":  # Pack Price
            # Set ratio for pack
            if length <= 60 and width <= 50 and height <= 30:  # pack size A
                self.request.session['ratio'] = 1.0
            elif length <= 80 and width <= 70 and height <= 50:  # pack size B
                self.request.session['ratio'] = 2.0
            elif length <= 100 and width <= 90 and height <= 70:  # pack size C
                self.request.session['ratio'] = 3.0
            # Set pack price
            if weight <= 1:
                col_name_pricing = 'up_to_1'
            elif weight <= 2:
                col_name_pricing = 'up_to_2'
            elif weight <= 5:
                col_name_pricing = 'up_to_5'
            elif weight <= 10:
                col_name_pricing = 'up_to_10'
            elif weight <= 15:
                col_name_pricing = 'up_to_15'
            elif weight <= 20:
                col_name_pricing = 'up_to_20'
            elif weight <= 30:
                col_name_pricing = 'up_to_30'

        elif type == "paleta":  # Pallet Price
            if weight <= 300:
                col_name_pricing = 'up_to_300'
            elif weight <= 500:
                col_name_pricing = 'up_to_500'
            elif weight <= 800:
                col_name_pricing = 'up_to_800'
            elif weight <= 1000:
                col_name_pricing = 'up_to_1000'

        return col_name_pricing

    def post(self, request, *args, **kwargs):
        form = FormParcelSize(request.POST)  # A form bound to the POST data

        if form.is_valid():
            # SESSION VARS
            type = request.POST['type']
            weight = float(request.POST['weight'])
            length = float(request.POST['length'])
            width = float(request.POST['width'])
            height = float(request.POST['height'])

            if type == "koperta":
                # envelope size: .5kg x 35cm x 25cm x 5cm
                if length > 35 or width > 25 or height > 5 or weight > 1:
                    context = {'form': form, 'error_parcel': 'Niepoprawne wymiary dla koperty!'}
                    return render(request, 'order/index.html', context)
            elif type == "paczka":
                # pack size: 30kg x 100cm x 90cm x 70cm
                if length > 100 or width > 90 or height > 70 or weight > 30:  # pack size C
                    context = {'form': form, 'error_parcel': 'Niepoprawne wymiary dla paczki!'}
                    return render(request, 'order/index.html', context)
            elif type == "paleta":
                # pallet size: 1000kg x 200cm x 140cm x 200cm
                if length > 200 or width > 140 or height > 200 or weight > 1000:  # pack size C
                    context = {'form': form, 'error_parcel': 'Niepoprawne wymiary dla palety!'}
                    return render(request, 'order/index.html', context)

            request.session['col_name_pricing'] = self.choose_pricing_col_and_ratio(type, weight, length, width, height)
            request.session['type'] = type
            request.session['weight'] = weight
            request.session['length'] = length
            request.session['width'] = width
            request.session['height'] = height
            return redirect('order:calculate')
        else:
            return render(request, 'order/index.html', {'form': form})


class CalculateView(generic.ListView):
    template_name = 'order/calculate.html'

    def post(self, request, *args, **kwargs):
        courier_id = request.session['courier_id'] = request.POST.get('courier')  # get courier_id from button
        if courier_id is None:
            request.session['error_courier'] = "Nie wybrałeś kuriera!"
            return redirect('order:calculate')
        if request.session.get('error_courier') is not None:
            del request.session['error_courier']

        col_name_pricing = request.session.get('col_name_pricing')
        type = request.session.get('type')  # get pack type from session
        ratio = request.session.get('ratio')

        if type == "koperta":
            query = list(
                EnvelopePricing.objects.filter(courier__id=courier_id).values(col_name_pricing))  # query: price from db
            price = query[0].get(col_name_pricing)  # value: price from query
            request.session['price'] = price  # save to session
        elif type == "paczka":
            query = list(PackPricing.objects.filter(courier__id=courier_id).values(col_name_pricing))
            price = query[0].get(col_name_pricing) * ratio
            request.session['price'] = price
        elif type == "paleta":
            query = list(PalletPricing.objects.filter(courier__id=courier_id).values(col_name_pricing))
            price = query[0].get(col_name_pricing)
            request.session['price'] = price
        return redirect('order:sender_address')

    def get_queryset(self):
        col_name_pricing = self.request.session.get('col_name_pricing')
        type = self.request.session.get('type')
        ratio = self.request.session.get('ratio')
        if type == 'koperta':
            return EnvelopePricing.objects.values_list('courier', 'courier__name', col_name_pricing)
        elif type == 'paczka':
            pack_price_col = list(PackPricing.objects.values_list('courier', 'courier__name', col_name_pricing))
            real_pack_price = list()

            for x in pack_price_col:
                price = round(x[2] * ratio, 2)
                real_pack_price.append(tuple([x[0], x[1], price]))
            return real_pack_price
        elif type == 'paleta':
            return PalletPricing.objects.values_list('courier', 'courier__name', col_name_pricing)


class AboutCompanyView(generic.TemplateView):
    template_name = 'order/about.html'


class CourierView(generic.TemplateView):
    template_name = 'order/courier.html'


class SenderAddressView(generic.FormView):
    template_name = 'order/sender_address.html'
    form_class = AddressForm

    def post(self, request, *args, **kwargs):
        form = AddressForm(request.POST)  # A form bound to the POST data
        if form.is_valid():
            request.session['sender_form'] = form.cleaned_data  # thanks to pickle serializer
            return redirect('order:recipient_address')
        else:
            return render(request, 'order/sender_address.html', {'form': form})


class RecipientAddressView(generic.FormView):
    template_name = 'order/recipient_address.html'
    form_class = AddressForm

    def post(self, request, *args, **kwargs):
        form = AddressForm(request.POST)  # A form bound to the POST data
        if form.is_valid():
            request.session['recipient_form'] = form.cleaned_data
            return redirect('order:summary')
        else:
            return render(request, 'order/recipient_address.html', {'form': form})


class SummaryView(generic.TemplateView):
    template_name = 'order/summary.html'

    def post(self, request, *args, **kwargs):
        # Creating parcel
        type = self.request.session.get('type')
        weight = float(self.request.session.get('weight'))
        length = float(self.request.session.get('length'))
        width = float(self.request.session.get('width'))
        height = float(self.request.session.get('height'))

        # Creating Parcel db
        parcel_obj = Parcel.objects.create(length=length, height=height, width=width, weight=weight, type=type)
        parcel_id = parcel_obj.id
        parcel_obj = Parcel.objects.get(id=parcel_id)

        # Creating Address for sender db
        sender_form = request.session.get('sender_form')
        sender_obj = Address(
            **sender_form)  # Unwrap the dictionary, making its keys and values act like named arguments

        # TODO clean the data before sending form !
        # sender_obj = sender_obj.save(commit=False) # now impossible

        # Save Address form
        sender_obj.save()
        sender_id = sender_obj.id
        sender_obj = Address.objects.get(id=sender_id)

        # Creating SenderAddress db
        sender_address_obj = SenderAddress.objects.create(address=sender_obj)
        sender_address_obj_id = sender_address_obj.id
        sender_address_obj = SenderAddress.objects.get(id=sender_address_obj_id)

        # Creating Address for recipient db
        recipient_form = request.session.get('recipient_form')
        recipient_obj = Address(**recipient_form)

        # Save Address form
        recipient_obj.save()
        recipient_id = recipient_obj.id
        recipient_obj = Address.objects.get(id=recipient_id)

        # Creating RecipientAddress db
        recipient_address_obj = RecipientAddress.objects.create(address=recipient_obj)
        recipient_address_obj_id = recipient_address_obj.id
        recipient_address_obj = RecipientAddress.objects.get(id=recipient_address_obj_id)

        # Creating order db
        profile_obj = Profile.objects.get(id=3)
        courier_id = int(request.session.get('courier_id'))
        courier_obj = Courier.objects.get(id=courier_id)

        price = float(request.session.get('price'))
        Order.objects.create(profile=profile_obj, courier=courier_obj, parcel=parcel_obj,
                             recipient=recipient_address_obj,
                             sender=sender_address_obj, price=price)

        # DEL session vars
        del request.session['type']
        del request.session['weight']
        del request.session['length']
        del request.session['width']
        del request.session['height']
        del request.session['courier_id']
        del request.session['price']
        del request.session['sender_form']
        del request.session['recipient_form']
        if request.session.get('ratio') is not None:
            del request.session['ratio']

        return redirect('order:index')


class PricingView(generic.ListView):
    template_name = 'order/pricing.html'

    def get_queryset(self):
        return Courier.objects.all()


class PricingCompanyView(generic.TemplateView):
    template_name = 'order/pricing_company.html'

    def get_context_data(self, **kwargs):
        context = super(PricingCompanyView, self).get_context_data(**kwargs)
        context['packpricing'] = PackPricing.objects.get(courier_id=self.kwargs['pk'])
        context['palletpricing'] = PalletPricing.objects.get(courier_id=self.kwargs['pk'])
        context['envelopepricing'] = EnvelopePricing.objects.get(courier_id=self.kwargs['pk'])
        return context


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('order:login')
    template_name = 'registration/signup.html'

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('order:index')
        return super().dispatch(*args, **kwargs)


class LogoutView(RedirectView):
    # Provides users the ability to logout
    url = '/'

    def get(self, request, *args, **kwargs):
        logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)
