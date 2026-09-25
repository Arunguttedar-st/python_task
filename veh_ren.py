class InvalidInputError(Exception):
  """Custom exception for invalid inputs."""

  pass


class VehicleNotFoundError(Exception):
  """Custom exception when a vehicle ID is not found."""

  pass


class VehicleNotAvailableError(Exception):
  """Custom exception when a vehicle is already rented."""

  pass


class DuplicateVehicleError(Exception):
  """Custom exception for duplicate vehicle IDs."""

  pass


class Vehicle:

  def __init__(self, vehicle_id: str, name: str, v_type: str, price: float):
    if not vehicle_id.strip():
      raise InvalidInputError("Vehicle ID cannot be empty.")
    if not name.strip():
      raise InvalidInputError("Vehicle name cannot be empty.")

    valid_types = ["Bike", "Car", "SUV"]
    if v_type not in valid_types:
      raise InvalidInputError(
          f"Invalid vehicle type. Must be one of {valid_types}."
      )

    if price <= 0:
      raise InvalidInputError("Rental price per day must be greater than 0.")

    self.vehicle_id = vehicle_id
    self.name = name
    self.v_type = v_type
    self.price = price
    self.is_available = True

  def __str__(self):
    status = "Available" if self.is_available else "Rented"
    return f"ID: {self.vehicle_id} | Name: {self.name} | Type: {self.v_type} | Price/Day: ${self.price:.2f} | Status: {status}"


class RentalSystem:

  def __init__(self):
    self.vehicles = {}  # vehicle_id -> Vehicle object
    self.rentals = {}  # customer_id -> dict of rental details

  def add_vehicle(
      self, vehicle_id: str, name: str, v_type: str, price: float
  ):
    if vehicle_id in self.vehicles:
      raise DuplicateVehicleError(
          f"Vehicle ID '{vehicle_id}' already exists."
      )
    vehicle = Vehicle(vehicle_id, name, v_type, price)
    self.vehicles[vehicle_id] = vehicle
    print(f"Success: Vehicle '{name}' added successfully.")

  def view_available_vehicles(self):
    available = [v for v in self.vehicles.values() if v.is_available]
    if not available:
      print("No vehicles currently available.")
      return
    print("\n--- Available Vehicles ---")
    for v in available:
      print(v)

  def rent_vehicle(
      self, customer_id: str, customer_name: str, vehicle_id: str, days: int
  ):
    if not customer_id.strip():
      raise InvalidInputError("Customer ID cannot be empty.")
    if not customer_name.strip():
      raise InvalidInputError("Customer name cannot be empty.")
    if customer_id in self.rentals:
      raise InvalidInputError(
          f"Customer ID '{customer_id}' already has an active rental."
      )
    if days <= 0:
      raise InvalidInputError("Rental days must be greater than 0.")

    if vehicle_id not in self.vehicles:
      raise VehicleNotFoundError(f"Vehicle ID '{vehicle_id}' not found.")

    vehicle = self.vehicles[vehicle_id]
    if not vehicle.is_available:
      raise VehicleNotAvailableError(
          f"Vehicle '{vehicle.name}' is currently rented out."
      )

    # Calculate Total Amount with 10% discount if days >= 7
    total_amount = vehicle.price * days
    if days >= 7:
      total_amount *= 0.90  # Apply 10% discount

    vehicle.is_available = False
    self.rentals[customer_id] = {
        "customer_name": customer_name,
        "vehicle_id": vehicle_id,
        "days": days,
        "total_amount": total_amount,
    }
    print(
        f"Success: Vehicle rented to {customer_name}. Total Amount: ${total_amount:.2f}"
    )

  def return_vehicle(self, vehicle_id: str):
    if vehicle_id not in self.vehicles:
      raise VehicleNotFoundError(f"Vehicle ID '{vehicle_id}' not found.")

    vehicle = self.vehicles[vehicle_id]
    if vehicle.is_available:
      print(f"Vehicle '{vehicle.name}' is already available.")
      return

    # Find and remove customer rental entry
    customer_to_remove = None
    for cust_id, rental in self.rentals.items():
      if rental["vehicle_id"] == vehicle_id:
        customer_to_remove = cust_id
        break

    if customer_to_remove:
      del self.rentals[customer_to_remove]

    vehicle.is_available = True
    print(
        f"Success: Vehicle '{vehicle.name}' has been returned and is now available."
    )

  def search_rental_by_customer(self, customer_id: str):
    if customer_id not in self.rentals:
      print(f"No active rental found for Customer ID '{customer_id}'.")
      return
    rental = self.rentals[customer_id]
    print(f"\n--- Rental Details for Customer: {customer_id} ---")
    print(f"Customer Name: {rental['customer_name']}")
    print(f"Vehicle ID: {rental['vehicle_id']}")
    print(f"Rental Days: {rental['days']}")
    print(f"Total Amount: ${rental['total_amount']:.2f}")

  def display_rented_vehicles(self):
    rented = [v for v in self.vehicles.values() if not v.is_available]
    if not rented:
      print("No vehicles currently rented out.")
      return
    print("\n--- Currently Rented Vehicles ---")
    for v in rented:
      print(v)

  def generate_summary_report(self):
    print("\n================ RENTAL SUMMARY REPORT ================")
    print(f"Total Vehicles in Fleet: {len(self.vehicles)}")
    available_count = sum(1 for v in self.vehicles.values() if v.is_available)
    rented_count = len(self.vehicles) - available_count
    print(f"Available Vehicles: {available_count}")
    print(f"Rented Vehicles: {rented_count}")
    print(f"Active Rentals Count: {len(self.rentals)}")
    total_revenue = sum(
        r["total_amount"] for r in self.rentals.values()
    )  # Note: represents active rentals revenue
    print(f"Current Active Rental Revenue: ${total_revenue:.2f}")
    print("=======================================================")


def main():
  system = RentalSystem()

  while True:
    print("\n=== Vehicle Rental Management System ===")
    print("1. Add New Vehicle")
    print("2. View Available Vehicles")
    print("3. Rent a Vehicle")
    print("4. Return a Vehicle")
    print("5. Search Rental Details by Customer ID")
    print("6. Display All Rented Vehicles")
    print("7. Generate Rental Summary Report")
    print("8. Exit")

    choice = input("Enter your choice (1-8): ").strip()

    try:
      if choice == "1":
        v_id = input("Enter Vehicle ID: ")
        name = input("Enter Vehicle Name: ")
        v_type = input("Enter Vehicle Type (Bike/Car/SUV): ")
        price = float(input("Enter Rental Price Per Day: "))
        system.add_vehicle(v_id, name, v_type, price)

      elif choice == "2":
        system.view_available_vehicles()

      elif choice == "3":
        c_id = input("Enter Customer ID: ")
        c_name = input("Enter Customer Name: ")
        v_id = input("Enter Vehicle ID to Rent: ")
        days = int(input("Enter Number of Rental Days: "))
        system.rent_vehicle(c_id, c_name, v_id, days)

      elif choice == "4":
        v_id = input("Enter Vehicle ID to Return: ")
        system.return_vehicle(v_id)

      elif choice == "5":
        c_id = input("Enter Customer ID to Search: ")
        system.search_rental_by_customer(c_id)

      elif choice == "6":
        system.display_rented_vehicles()

      elif choice == "7":
        system.generate_summary_report()

      elif choice == "8":
        print("Exiting application. Goodbye!")
        break
      else:
        print("Invalid choice! Please select between 1 and 8.")

    except ValueError:
      print("Error: Please enter valid numerical values for price or days.")
    except (
        InvalidInputError,
        VehicleNotFoundError,
        VehicleNotAvailableError,
        DuplicateVehicleError,
    ) as e:
      print(f"Error: {e}")


if __name__ == "__main__":
  main()