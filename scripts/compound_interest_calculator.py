#!/usr/bin/env python
import argparse
import itertools as it
import tkinter as tk
# Import `TkAgg` backend to use Matplotlib with Tkinter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt

# Program to demonstrate the power of compounding interest

# Parse command line options
parser = argparse.ArgumentParser()
parser.add_argument('-p','--plot', help='show plots of value and interest',
                    action='store_true')
args = parser.parse_args()


def calc_amount(principal, freq, rate, time):
    """Calculate value with compounding interest."""
    A = principal*(1 + rate/freq)**(freq*time)
    return A

def calc_amount_with_cont(principal, cont, freq, rate, time):
    """Calculate value with compounding interest and a monthly contribution."""
    base_value = calc_amount(principal, freq, rate, time)
    cont_value = cont*((1 + rate/freq)**(freq*time) - 1)/(rate/freq)
    A = base_value + cont_value
    return A

def calc_amount_by_year(principal, cont, freq, rate, time_range):
    """Calculate the value for all years in a range."""
    A = [calc_amount_with_cont(principal, cont, freq, rate, time)
         for time in time_range]
    return A

def calc_interest(initial_amount, final_amount, cont, freq):
    """Calculate the interest added from one year to the next."""
    IA = final_amount - (initial_amount + cont*freq)
    return IA

def calc_interest_by_year(amounts_by_year, cont, freq):
    """Calculate the interest added in a year for all years in a range."""
    IA = [calc_interest(amounts_by_year[i-1], amounts_by_year[i], cont, freq)
          if i != 0 else 0 for i in range(len(amounts_by_year))]
    return IA

def convert_to_money(value):
    return f'${value:,.2f}'

class Application(tk.Frame):

    def __init__(self, master=None):
        # Set application default values
        self.principal = 16_000
        self.contribution = 500
        self.rate = 3
        self.frequency = 12
        self.years = 45
        self.starting_year = 2020
        self.ending_year = self.starting_year + self.years
        self.time_range = range(self.years+1)
        self.year_range = range(self.starting_year, self.ending_year+1)
        # Define column indices and widths
        self.title_col, self.unit_col, self.entry_col = 1, 2, 3
        self.year_col, self.amount_col, self.interest_col = 4, 5, 6
        self.year_width, self.amount_width, self.interest_width = 5, 13, 13
        self.year_padx = 20
        self.amount_align, self.interest_align = 'e', 'e'
        # Pick years to give amounts for, progressively larger gaps
        if self.years < 10:
            self.display_years = list(range(1, self.years+1))
        if self.years >= 10:
            self.display_years = (list(range(1, 10)) +
                                  list(range(10, self.years+1, 5)))

        # Define field names and display formats
        self.fields = {'principal': ('Principal', '$',
                                     f'{self.principal:,.2f}', float),
                       'contribution': ('Contribution', '$',
                                        f'{self.contribution:,.2f}', float),
                       'rate': ('Rate', '%',
                                f'{self.rate:.1f}', float),
                       'frequency': ('Frequency', '',
                                     f'{self.frequency}', int),
                       'years': ('Years', '',
                                 f'{self.years}', int),
                       'starting_year': ('Starting Year', '',
                                         f'{self.starting_year}', int)}

        # Initialize the GUI
        super().__init__(master, padx=20, pady=20)
        self.grid()
        self.create_widgets()

    def create_widgets(self):
        row_counter = it.count(1)
        for field in self.fields:
            # Set the field entry boxes and corresponding labels
            label = tk.Label(self, text=self.fields[field][0])
            unit_label = tk.Label(self, text=self.fields[field][1])
            entry = tk.Entry(self, width=10)
            entry_attr = f'{field}_entry'
            self.__setattr__(entry_attr, entry)
            # Position the entry boxes
            row = next(row_counter)
            label.grid(row=row, column=self.title_col, sticky=tk.W)
            unit_label.grid(row=row, column=self.unit_col, sticky=tk.E)
            entry.grid(row=row, column=self.entry_col)
            # Fill entry boxes with defaults
            entry.insert(0, self.fields[field][2])

        # Set the calculate and quit buttons
        self.calc_button = tk.Button(self, text='Calculate',
                                     command=lambda: self.calc())
        self.quit_button = tk.Button(self, text='Quit',
                                     command=self.quit)
        # Position the buttons 
        next(row_counter)
        self.calc_button.grid(row=next(row_counter), rowspan=2,
                              column=2, sticky=tk.N+tk.S)
        next(row_counter)
        next(row_counter)
        self.quit_button.grid(row=next(row_counter), column=2)

        # Display the calculator outputs
        (tk.Label(self, text='Year')
         .grid(row=0, column=self.year_col))
        (tk.Label(self, text='Amount', anchor='e')
         .grid(row=0, column=self.amount_col, sticky=self.interest_align))
        (tk.Label(self, text='Interest', anchor='e')
         .grid(row=0, column=self.interest_col, sticky=self.interest_align))
        for row_i ,year in enumerate(self.display_years):
            (tk.Label(self, width=self.year_width, padx=self.year_padx)
             .grid(row=row_i+1, column=self.year_col, sticky='w'))
            (tk.Label(self, width=self.amount_width)
             .grid(row=row_i+1, column=self.amount_col,
                   sticky=self.amount_align))
            (tk.Label(self, width=self.interest_width)
             .grid(row=row_i+1, column=self.interest_col,
                   sticky=self.interest_align))

    def calc(self):

        # Get values from entry fields
        for field in self.fields:
            field_value = self.__getattribute__(f'{field}_entry').get()
            field_value = field_value.replace(',', '')
            self.__setattr__(field, self.fields[field][3](field_value))
        self.ending_year = self.starting_year + self.years
        self.time_range = range(self.years+1)
        self.year_range = range(self.starting_year, self.ending_year+1)

        A = calc_amount_by_year(self.principal, self.contribution,
                                self.frequency, self.rate/100, self.time_range)
        IA = calc_interest_by_year(A, self.contribution, self.frequency)

        for row_i ,year_i in enumerate(self.display_years):
            (tk.Label(self, text=f'{self.starting_year+year_i} ({year_i})',
                      width=self.year_width, padx=self.year_padx, anchor=tk.W)
             .grid(row=row_i+1, column=self.year_col))
            (tk.Label(self, text=f'{convert_to_money(A[year_i])}',
                      width=self.amount_width, anchor=tk.E)
             .grid(row=row_i+1, column=self.amount_col,
                   sticky=self.amount_align))
            (tk.Label(self, text=f'{convert_to_money(IA[year_i])}',
                      width=self.interest_width, anchor=tk.E)
             .grid(row=row_i+1, column=self.interest_col,
                   sticky=self.amount_align))

        # Plot the interest
        if args.plot:
            raise NotImplementedError("Plots haven't been worked in yet")
            ax1 = plt.subplot(211)
            ax1.scatter(self.year_range, A[1:])
            ax1.set_title('Fund Amount')
            ax2 = plt.subplot(212, sharex=ax1)
            ax2.scatter(self.year_range, IA[1:])
            ax2.set_title('Interest earned')
            plt.tight_layout()
            plt.show()

if __name__ == '__main__':
    app = Application()
    app.master.title('Compound Interest Calculator')
    app.mainloop()
